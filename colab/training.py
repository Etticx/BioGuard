"""BioGuard: three architectures, validation-only recipe selection, app-compatible export."""
import gc
import hashlib
import json
import math
import platform
import shutil
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import numpy as np
from PIL import Image, ImageOps
import tensorflow as tf
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
import matplotlib.pyplot as plt

ARCHITECTURES = ("MobileNetV2", "MobileNetV3Large", "EfficientNetV2B0")
RECIPES = (
    {"name": "gentle", "dropout": 0.30, "head_lr": 1e-3, "fine_lr": 1e-5, "unfreeze_fraction": 0.25},
    {"name": "broader", "dropout": 0.40, "head_lr": 5e-4, "fine_lr": 3e-5, "unfreeze_fraction": 0.50},
)

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def extract_dataset(archive_path, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if len(members) > 10000 or sum(info.file_size for info in members) > 2 * 1024**3:
            raise ValueError("Unexpected dataset archive size.")
        names = [info.filename for info in members]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate paths in archive.")
        for info in members:
            name = PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in info.filename or ":" in info.filename:
                raise ValueError("Unsafe archive path.")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Archive symlinks are unsupported.")
            if not (destination / info.filename).resolve().is_relative_to(destination):
                raise ValueError("Archive path leaves extraction folder.")
        required = {"split_manifest.jsonl", "class_names.json", "species_policy.json", "dataset_metadata.json"}
        if not required.issubset(names):
            raise ValueError("Upload the comparison DATASET ZIP, not a model ZIP.")
        for info in members:
            target = destination / info.filename
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
    return destination

def audit_bundle(data_root):
    root = Path(data_root).resolve()
    classes = read_json(root / "class_names.json")
    rows = [json.loads(line) for line in (root / "split_manifest.jsonl").read_text("utf-8").splitlines() if line.strip()]
    if len(classes) != 9 or len(set(classes)) != 9:
        raise ValueError("Expected nine unique species.")
    ids = set()
    partitions = {key: defaultdict(set) for key in ("group", "observer_id", "observation_id", "sha256")}
    for row in rows:
        if row["split"] not in {"train", "validation", "test"}:
            raise ValueError("Unrecognised split.")
        if row["species"] != classes[int(row["label"])]:
            raise ValueError("Species/class-index mismatch.")
        if row["photo_id"] in ids:
            raise ValueError("Duplicate photo ID.")
        ids.add(row["photo_id"])
        path = (root / row["relative_path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Missing or unsafe image path.")
        if file_sha(path) != row["sha256"]:
            raise ValueError("Image checksum mismatch: " + str(row["photo_id"]))
        with Image.open(path) as image:
            image.load()
        for key in partitions:
            partitions[key][str(row[key])].add(row["split"])
    for key, values in partitions.items():
        if any(len(splits) > 1 for splits in values.values()):
            raise ValueError("Cross-split overlap: " + key)
    for split in ("train", "validation", "test"):
        if {int(row["label"]) for row in rows if row["split"] == split} != set(range(9)):
            raise ValueError("Every species must be represented in every split.")
    return rows, classes, {
        "images": len(rows), "split_counts": dict(Counter(row["split"] for row in rows)),
        "source_hashes_verified": True, "cross_split_groups_observers_observations_hashes": 0,
        "manual_image_review_complete": False, "botanical_labels_expert_verified": False,
    }

def prepare_image(path, size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image = ImageOps.pad(image, (size, size), method=Image.Resampling.BILINEAR,
                             color=(0, 0, 0), centering=(0.5, 0.5))
        return np.asarray(image, dtype=np.uint8)

def load_split(rows, root, split, size, smoke=False):
    selected = [row for row in rows if row["split"] == split]
    if smoke:
        limit = 2 if split == "train" else 1
        counts = Counter()
        subset = []
        for row in selected:
            if counts[row["label"]] < limit:
                subset.append(row)
                counts[row["label"]] += 1
        selected = subset
    pixels = np.stack([prepare_image(Path(root) / row["relative_path"], size) for row in selected])
    labels = np.array([int(row["label"]) for row in selected], dtype=np.int32)
    return pixels, labels, selected

def make_dataset(images, labels, batch, training=False, seed=42):
    dataset = tf.data.Dataset.from_tensor_slices((images, labels))
    if training:
        dataset = dataset.shuffle(len(labels), seed=seed, reshuffle_each_iteration=True)
    dataset = dataset.map(lambda image, label: (tf.cast(image, tf.float32), label), num_parallel_calls=2)
    options = tf.data.Options()
    options.experimental_deterministic = True
    options.threading.private_threadpool_size = 2
    options.threading.max_intra_op_parallelism = 1
    return dataset.batch(batch).with_options(options).prefetch(1)

def scores(labels, probabilities, classes):
    probabilities = np.asarray(probabilities)
    if probabilities.shape != (len(labels), len(classes)) or not np.isfinite(probabilities).all():
        raise ValueError("Invalid model probabilities.")
    if np.any(probabilities < 0) or np.any(probabilities > 1):
        raise ValueError("Probabilities outside [0,1].")
    np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-4)
    predicted = probabilities.argmax(axis=1)
    return {
        "accuracy": float(accuracy_score(labels, predicted)),
        "macro_f1": float(f1_score(labels, predicted, labels=list(range(len(classes))),
                                   average="macro", zero_division=0)),
    }

def build_model(architecture, recipe, config):
    size, seed = config["image_size"], config["seed"]
    kwargs = {"include_top": False, "weights": None if config["smoke_test"] else "imagenet",
              "input_shape": (size, size, 3)}
    if architecture == "MobileNetV2":
        base = tf.keras.applications.MobileNetV2(**kwargs)
    elif architecture == "MobileNetV3Large":
        base = tf.keras.applications.MobileNetV3Large(include_preprocessing=True, **kwargs)
    elif architecture == "EfficientNetV2B0":
        base = tf.keras.applications.EfficientNetV2B0(include_preprocessing=True, **kwargs)
    else:
        raise ValueError("Unsupported architecture.")
    base.trainable = False
    inputs = tf.keras.Input((size, size, 3), dtype="float32", name="rgb_pixels_0_255")
    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal", seed=seed),
        tf.keras.layers.RandomRotation(0.08, seed=seed + 1),
        tf.keras.layers.RandomZoom(0.10, seed=seed + 2),
        tf.keras.layers.RandomContrast(0.10, seed=seed + 3),
    ], name="train_augmentation")
    pixels = augmentation(inputs)
    if architecture == "MobileNetV2":
        pixels = tf.keras.layers.Rescaling(1 / 127.5, offset=-1, name="mobilenet_normalisation")(pixels)
    # V3 and EfficientNetV2 contain their own input rescaling. Never normalise twice.
    features = base(pixels, training=False)
    features = tf.keras.layers.GlobalAveragePooling2D()(features)
    features = tf.keras.layers.Dropout(recipe["dropout"], seed=seed + 4)(features)
    outputs = tf.keras.layers.Dense(9, activation="softmax", dtype="float32", name="species")(features)
    return tf.keras.Model(inputs, outputs, name="bioguard_" + architecture.lower()), base.name

def configure_fine_tuning(model, base_name, fraction):
    base = model.get_layer(base_name)
    base.trainable = True
    cutoff = len(base.layers) - max(1, math.ceil(len(base.layers) * fraction))
    for index, layer in enumerate(base.layers):
        layer.trainable = index >= cutoff and not isinstance(layer, tf.keras.layers.BatchNormalization)
    assert all(not layer.trainable for layer in base.layers
               if isinstance(layer, tf.keras.layers.BatchNormalization))
    return sum(layer.trainable for layer in base.layers)

class ValidationF1(tf.keras.callbacks.Callback):
    def __init__(self, dataset, labels):
        super().__init__()
        self.dataset, self.labels = dataset, labels
    def on_epoch_end(self, epoch, logs=None):
        if logs is not None:
            predicted = self.model.predict(self.dataset, verbose=0).argmax(axis=1)
            logs["val_macro_f1"] = float(f1_score(
                self.labels, predicted, labels=list(range(9)), average="macro", zero_division=0))
            logs["learning_rate"] = float(tf.keras.backend.get_value(self.model.optimizer.learning_rate))

def run_stage(model, stage_root, train_ds, val_ds, y_val, learning_rate, epochs, classes):
    stage_root = Path(stage_root)
    attempt = stage_root / datetime.now(timezone.utc).strftime("attempt_%Y%m%d_%H%M%S_%f")
    attempt.mkdir(parents=True, exist_ok=False)
    best = attempt / "best.keras"
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate),
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(), metrics=["accuracy"])
    callbacks = [
        ValidationF1(val_ds, y_val),
        tf.keras.callbacks.TerminateOnNaN(),
        tf.keras.callbacks.ModelCheckpoint(str(best), monitor="val_macro_f1", mode="max", save_best_only=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", mode="min", factor=0.5,
                                           patience=2, min_lr=1e-7),
        tf.keras.callbacks.EarlyStopping(monitor="val_macro_f1", mode="max", patience=5,
                                        min_delta=1e-4, restore_best_weights=False),
        tf.keras.callbacks.CSVLogger(str(attempt / "training_log.csv")),
    ]
    started = time.perf_counter()
    history = model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=callbacks, verbose=2)
    elapsed = time.perf_counter() - started
    if not best.exists() or not np.isfinite(history.history["loss"]).all():
        raise RuntimeError("Training did not produce a valid best checkpoint.")
    del model
    gc.collect()
    selected = tf.keras.models.load_model(best, compile=False)
    metrics = scores(y_val, selected.predict(val_ds, verbose=0), classes)
    result = {
        "checkpoint": str(best.resolve()), "checkpoint_sha256": file_sha(best),
        "validation_accuracy": metrics["accuracy"], "validation_macro_f1": metrics["macro_f1"],
        "epochs_completed": len(history.epoch), "training_seconds": elapsed,
        "history": {key: [float(value) for value in values] for key, values in history.history.items()},
    }
    write_json(stage_root / "complete.json", result)
    del selected
    tf.keras.backend.clear_session()
    gc.collect()
    return result

def completed_stage(stage_root):
    path = Path(stage_root) / "complete.json"
    if not path.exists():
        return None
    result = read_json(path)
    checkpoint = Path(result["checkpoint"])
    if not checkpoint.is_file() or file_sha(checkpoint) != result["checkpoint_sha256"]:
        raise ValueError("A completed checkpoint is missing or changed: " + str(stage_root))
    return result

def compare_models(config, data_root, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if config["smoke_test"]:
        print("SMOKE TEST: random initial weights, tiny subsets; scores are NOT accuracy evidence.")
    elif not tf.config.list_physical_devices("GPU") and config.get("require_gpu", True):
        raise RuntimeError("Select a GPU runtime in Colab.")
    tf.keras.mixed_precision.set_global_policy("float32")
    tf.keras.utils.set_random_seed(config["seed"])
    tf.config.experimental.enable_op_determinism()
    rows, classes, audit = audit_bundle(data_root)
    write_json(output / "data_audit.json", audit)
    signature = {
        "config": config, "architectures": ARCHITECTURES,
        "recipes": RECIPES[:1] if config["smoke_test"] else RECIPES,
        "split_manifest_sha256": file_sha(Path(data_root) / "split_manifest.jsonl"),
        "tensorflow": tf.__version__, "keras": tf.keras.__version__,
        "training_source_sha256": config.get("training_source_sha256", "not-recorded"),
    }
    fingerprint = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
    metadata_path = output / "experiment.json"
    if metadata_path.exists() and read_json(metadata_path)["fingerprint"] != fingerprint:
        raise ValueError("Settings/data/runtime changed. Choose a NEW RUN_ID instead of mixing experiments.")
    write_json(metadata_path, {"fingerprint": fingerprint, **signature})
    train_x, train_y, _ = load_split(rows, data_root, "train", config["image_size"], config["smoke_test"])
    val_x, val_y, val_rows = load_split(rows, data_root, "validation", config["image_size"], config["smoke_test"])
    train_ds = make_dataset(train_x, train_y, config["batch_size"], True, config["seed"])
    val_ds = make_dataset(val_x, val_y, config["batch_size"])
    results = []
    recipes = RECIPES[:1] if config["smoke_test"] else RECIPES
    for architecture in ARCHITECTURES:
        for recipe in recipes:
            trial = output / (architecture + "__" + recipe["name"])
            trial.mkdir(exist_ok=True)
            tf.keras.backend.clear_session()
            tf.keras.utils.set_random_seed(config["seed"])
            head = completed_stage(trial / "head")
            if head is None:
                print("\nTraining", architecture, recipe["name"], "frozen head")
                model, base_name = build_model(architecture, recipe, config)
                write_json(trial / "base.json", {"name": base_name, "recipe": recipe})
                head = run_stage(model, trial / "head", train_ds, val_ds, val_y,
                                 recipe["head_lr"], 1 if config["smoke_test"] else config["head_epochs"], classes)
                del model
            else:
                print("Resuming completed head:", architecture, recipe["name"])
            base_name = read_json(trial / "base.json")["name"]
            fine = completed_stage(trial / "fine")
            if fine is None:
                model = tf.keras.models.load_model(head["checkpoint"], compile=False)
                count = configure_fine_tuning(model, base_name, recipe["unfreeze_fraction"])
                print("Fine-tuning", architecture, recipe["name"], "trainable base layers:", count)
                fine = run_stage(model, trial / "fine", train_ds, val_ds, val_y,
                                 recipe["fine_lr"], 1 if config["smoke_test"] else config["fine_epochs"], classes)
                del model
            else:
                print("Resuming completed fine-tune:", architecture, recipe["name"])
            for stage, record in (("head", head), ("fine", fine)):
                results.append({"architecture": architecture, "recipe": recipe, "stage": stage, **record})
            write_json(output / "validation_comparison.json", results)
            gc.collect()
    # All model/recipe/stage choices are frozen before test pixels are loaded.
    winners = []
    for architecture in ARCHITECTURES:
        candidates = [row for row in results if row["architecture"] == architecture]
        winner = max(candidates, key=lambda row: row["validation_macro_f1"])
        winners.append(winner)
    global_winner = max(winners, key=lambda row: row["validation_macro_f1"])
    locked = {"criterion": "validation macro F1 only", "fingerprint": fingerprint,
              "architecture_winners": winners, "winner": global_winner}
    lock_path = output / "locked_selection.json"
    if lock_path.exists() and read_json(lock_path) != locked:
        raise ValueError("Locked selection changed; create a new run.")
    write_json(lock_path, locked)
    return {"rows": rows, "classes": classes, "audit": audit, "val_x": val_x, "val_y": val_y,
            "val_rows": val_rows, "locked": locked, "config": config, "root": str(data_root),
            "output": str(output), "validation_results": results}

def choose_threshold(labels, probabilities):
    confidence, predicted = probabilities.max(axis=1), probabilities.argmax(axis=1)
    candidates = []
    minimum = min(len(labels), max(30, math.ceil(len(labels) * 0.5)))
    for threshold in np.arange(0.50, 1.00, 0.02):
        retained = confidence >= threshold
        if retained.sum() >= minimum:
            accuracy = float(np.mean(predicted[retained] == labels[retained]))
            if accuracy >= 0.90:
                candidates.append({"threshold": float(round(threshold, 2)),
                                   "retained": int(retained.sum()), "coverage": float(retained.mean()),
                                   "accuracy": accuracy})
    return max(candidates, key=lambda item: item["coverage"]) if candidates else None

def evaluate_locked_models(state):
    output, config = Path(state["output"]), state["config"]
    cached = output / "historical_test_comparison.json"
    lock = read_json(output / "locked_selection.json")
    if lock != state["locked"]:
        raise ValueError("Selection lock changed.")
    if cached.exists():
        result = read_json(cached)
        if result["fingerprint"] != lock["fingerprint"]:
            raise ValueError("Test cache belongs to another experiment.")
        return result
    images, labels, records = load_split(state["rows"], state["root"], "test",
                                        config["image_size"], config["smoke_test"])
    dataset = make_dataset(images, labels, config["batch_size"])
    reports = []
    for winner in lock["architecture_winners"]:
        if file_sha(winner["checkpoint"]) != winner["checkpoint_sha256"]:
            raise ValueError("Selected model checkpoint changed.")
        tf.keras.backend.clear_session()
        model = tf.keras.models.load_model(winner["checkpoint"], compile=False)
        probabilities = model.predict(dataset, verbose=0)
        report = {**scores(labels, probabilities, state["classes"]),
                  "architecture": winner["architecture"], "recipe": winner["recipe"]["name"],
                  "stage": winner["stage"], "test_images": len(labels),
                  "classification_report": classification_report(
                      labels, probabilities.argmax(axis=1), labels=list(range(9)),
                      target_names=state["classes"], output_dict=True, zero_division=0),
                  "confusion_matrix": confusion_matrix(labels, probabilities.argmax(axis=1),
                                                       labels=list(range(9))).tolist()}
        reports.append(report)
        predictions = [
            {**row, "predicted_species": state["classes"][int(prob.argmax())],
             "confidence": float(prob.max())}
            for row, prob in zip(records, probabilities)
        ]
        (output / (winner["architecture"] + "_test_predictions.jsonl")).write_text(
            "\n".join(json.dumps(row) for row in predictions) + "\n", encoding="utf-8")
        del model
        gc.collect()
    result = {
        "fingerprint": lock["fingerprint"], "run_type": "smoke_test_only" if config["smoke_test"] else "full_training",
        "test_set_status": "historical_holdout_previously_inspected_not_fresh_field_validation",
        "selection_used_test_results": False, "models": reports,
        "historical_baseline": read_json(Path(state["root"]) / "historical_evaluation.json"),
    }
    write_json(cached, result)
    return result

def draw_results(state, test_result):
    output = Path(state["output"])
    names = [item["architecture"] for item in state["locked"]["architecture_winners"]]
    values = [item["validation_macro_f1"] for item in state["locked"]["architecture_winners"]]
    fig, axis = plt.subplots(figsize=(9, 4))
    axis.barh(names, values, color="#235B42")
    axis.set_xlim(0, 1)
    axis.set_xlabel("Validation macro F1 (0–1)")
    axis.set_ylabel("Architecture (best recipe and stage)")
    axis.set_title("Validation comparison" + (" — SMOKE TEST ONLY" if state["config"]["smoke_test"] else ""))
    fig.tight_layout(); fig.savefig(output / "validation_comparison.png", dpi=140); plt.show()
    winner_name = state["locked"]["winner"]["architecture"]
    selected_test = next(row for row in test_result["models"] if row["architecture"] == winner_name)
    fig, axis = plt.subplots(figsize=(10, 8))
    image = axis.imshow(selected_test["confusion_matrix"], cmap="Greens")
    axis.set_xticks(range(9), state["classes"], rotation=90)
    axis.set_yticks(range(9), state["classes"])
    axis.set_xlabel("Predicted species"); axis.set_ylabel("Dataset species label")
    axis.set_title(winner_name + " — historical test confusion matrix")
    fig.colorbar(image, ax=axis, label="Photos (count)")
    fig.tight_layout(); fig.savefig(output / "test_confusion_matrix.png", dpi=140); plt.show()

def export_package(state, test_result):
    output, config = Path(state["output"]), state["config"]
    winner = state["locked"]["winner"]
    package = output / ("SMOKE_TEST_ONLY_model_package" if config["smoke_test"] else "model_package")
    package.mkdir(exist_ok=True)
    tf.keras.backend.clear_session()
    model = tf.keras.models.load_model(winner["checkpoint"], compile=False)
    val_ds = make_dataset(state["val_x"], state["val_y"], config["batch_size"])
    probabilities = model.predict(val_ds, verbose=0)
    threshold = choose_threshold(state["val_y"], probabilities)
    selection = {
        **state["locked"], "review_threshold": None if threshold is None else threshold["threshold"],
        "threshold_validation_estimate": threshold, "threshold_is_not_unknown_species_detection": True,
    }
    selected_test = next(row for row in test_result["models"] if row["architecture"] == winner["architecture"])
    retained = np.zeros(selected_test["test_images"], dtype=bool)
    evaluation = {
        "run_type": test_result["run_type"], "test_accuracy": selected_test["accuracy"],
        "test_macro_f1": selected_test["macro_f1"], "test_images": selected_test["test_images"],
        "classification_report": selected_test["classification_report"],
        "confusion_matrix": selected_test["confusion_matrix"],
        "test_set_status": test_result["test_set_status"],
        "selection_used_test_results": False, "manual_image_review_complete": False,
        "botanical_labels_expert_verified": False, "sdp_field_validation_performed": False,
        "limitations": ["Nine known species only; unknown species may receive high confidence.",
                        "Existing historical test images were previously inspected.",
                        "No independent field validation; no automatic removal authorised."],
    }
    source_root = Path(state["root"])
    for name in ("class_names.json", "species_policy.json", "split_manifest.jsonl", "dataset_metadata.json"):
        shutil.copy2(source_root / name, package / name)
    write_json(package / "selection.json", selection)
    write_json(package / "evaluation.json", evaluation)
    write_json(package / "data_audit.json", state["audit"])
    write_json(package / "preprocessing.json", {
        "image_size": config["image_size"], "colour": "RGB", "exif_transpose": True,
        "resize": "PIL.ImageOps.pad", "resample": "BILINEAR", "pad_colour": [0, 0, 0],
        "centering": [0.5, 0.5], "input_range": [0, 255], "input_dtype": "float32",
        "normalisation": "embedded model-specific preprocessing; do not normalise externally",
        "training_augmentation_only": True, "architecture": winner["architecture"],
    })
    environment = {
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": {"tensorflow": tf.__version__, "keras": tf.keras.__version__,
                     "numpy": np.__version__, "pillow": Image.__version__},
        "seed": config["seed"], "experiment": config, "gpu_devices": [str(x) for x in tf.config.list_physical_devices("GPU")],
        "utc_export_time": datetime.now(timezone.utc).isoformat(),
    }
    write_json(package / "environment.json", environment)
    for name in ("validation_comparison.json", "historical_test_comparison.json",
                 "validation_comparison.png", "test_confusion_matrix.png", "experiment.json"):
        if (output / name).exists():
            shutil.copy2(output / name, package / name)
    helper = source_root / "predict.py"
    if helper.exists():
        shutil.copy2(helper, package / "predict.py")
    for row in state["validation_results"]:
        log = Path(row["checkpoint"]).parent / "training_log.csv"
        target = row["architecture"] + "_" + row["recipe"]["name"] + "_" + row["stage"] + "_training_log.csv"
        if log.exists():
            shutil.copy2(log, package / target)
    model.save(package / "bioguard.keras")
    before = model(state["val_x"][:1].astype(np.float32), training=False).numpy()
    del model
    tf.keras.backend.clear_session(); gc.collect()
    # Load on CPU to check portable inference and label consistency for the laptop API.
    with tf.device("/CPU:0"):
        reloaded = tf.keras.models.load_model(package / "bioguard.keras", compile=False)
        probe = state["val_x"][:1].astype(np.float32)
        after = reloaded(probe, training=False).numpy()
        np.testing.assert_allclose(before, after, rtol=2e-3, atol=2e-4)
        assert reloaded.output_shape[-1] == len(state["classes"])
        for _ in range(3):
            reloaded(probe, training=False).numpy()
        times = []
        for _ in range(10):
            started = time.perf_counter()
            reloaded(probe, training=False).numpy()
            times.append((time.perf_counter() - started) * 1000)
    write_json(package / "cpu_reload_check.json", {
        "passed": True, "median_single_photo_ms": float(np.median(times)),
        "device": "CPU of the machine running this notebook; not a phone/laptop benchmark",
    })
    requirements = "\n".join(name + "==" + version for name, version in environment["packages"].items()) + "\n"
    (package / "requirements-tested.txt").write_text(requirements, encoding="utf-8")
    (package / "READ_ME_FIRST.txt").write_text(
        "BioGuard three-model experiment\nRun type: " + test_result["run_type"] +
        "\nArchitecture: " + winner["architecture"] +
        "\nSelected by validation macro F1 only. Test results did not choose the winner." +
        "\nHistorical test accuracy: " + str(selected_test["accuracy"]) +
        "\nHistorical test macro F1: " + str(selected_test["macro_f1"]) +
        "\nThe historical holdout was previously inspected; fresh field evaluation is still required." +
        "\nInput: EXIF -> RGB -> aspect-preserving black padding, float32 0–255." +
        "\nNormalisation is embedded. Preserve class_names.json order." +
        "\nNine supported species only. Confidence does not reliably reject unknown species." +
        "\nManual review unfinished; botanical labels not independently verified." +
        "\nNo automatic ecological treatment/removal is authorised." +
        "\nPreserve per-image licences and attribution in split_manifest.jsonl.\n", encoding="utf-8")
    name = "bioguard_SMOKE_TEST_ONLY" if config["smoke_test"] else "bioguard_comparison_winner"
    archive = Path(shutil.make_archive(str(output / name), "zip", package))
    return archive

