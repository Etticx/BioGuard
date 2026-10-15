"""Build a standalone notebook and frozen-data ZIP without changing original photos."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
MODEL_PACKAGE = PROJECT / "backend" / "model"
SOURCE = PROJECT.parent / "SDHackathon" / "data" / "bioguard"

def main():
    source = (ROOT / "training.py").read_text(encoding="utf-8-sig")
    ast.parse(source)
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    rows = [json.loads(line) for line in (MODEL_PACKAGE / "split_manifest.jsonl").read_text("utf-8").splitlines() if line]
    metadata = {
        "dataset_version": "original-2700-fixed-splits",
        "source": "iNaturalist Licensed Observation Images, curated subset",
        "images": len(rows), "split_counts": dict(Counter(row["split"] for row in rows)),
        "manual_image_review_complete": False, "botanical_labels_expert_verified": False,
        "test_set_status": "historical_holdout_previously_inspected_not_fresh_field_validation",
        "note": "Review decisions have not been applied. Original photos, labels and splits preserved.",
        "split_manifest_sha256": hashlib.sha256((MODEL_PACKAGE / "split_manifest.jsonl").read_bytes()).hexdigest(),
    }
    data_zip = ROOT / "bioguard_comparison_dataset.zip"
    if not data_zip.exists():
        with zipfile.ZipFile(data_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for name in ("split_manifest.jsonl", "class_names.json", "species_policy.json", "predict.py"):
                archive.write(MODEL_PACKAGE / name, name)
            archive.write(MODEL_PACKAGE / "evaluation.json", "historical_evaluation.json")
            archive.writestr("dataset_metadata.json", json.dumps(metadata, indent=2))
            for index, row in enumerate(rows, 1):
                image = SOURCE / row["relative_path"]
                if hashlib.sha256(image.read_bytes()).hexdigest() != row["sha256"]:
                    raise ValueError("Source checksum mismatch: " + str(image))
                archive.write(image, row["relative_path"])
                if index % 500 == 0:
                    print("Packaged", index, "of", len(rows), "photos", flush=True)
    else:
        with zipfile.ZipFile(data_zip) as archive:
            if json.loads(archive.read("dataset_metadata.json")) != metadata:
                raise ValueError("Existing dataset ZIP differs; preserve it and use a new filename.")
    cells = []
    def md(text):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)})
    def code(text):
        ast.parse(text)
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                      "source": text.splitlines(keepends=True)})
    md("""# BioGuard: three models + training improvements
Compare **MobileNetV2**, **MobileNetV3 Large** and **EfficientNetV2-B0** on the same frozen nine-species dataset.

**Step 3:** compare architectures. **Step 4:** two matched training recipes per architecture:
different dropout, learning rates and fine-tuning depth; shared realistic augmentation,
early stopping, automatic learning-rate reduction and validation-macro-F1 checkpoints.

Each model trains separately. The app will use one validation-selected winner.

## Before starting
1. Choose **Runtime → Change runtime type → T4 GPU** (or another available GPU).
2. Put **bioguard_comparison_dataset.zip** in **My Drive / BioGuard**.
3. Keep **SMOKE_TEST = False** for the real comparison.
4. Run the cells in order. The default is **six trials**, each with frozen-head training and fine-tuning.

GPU availability and runtime vary. No fixed completion time is promised.
Photo review remains unfinished: this uses the **original 2,700 photos**.
The 380 test images were inspected previously; they are a **historical benchmark**,
not a new untouched field test. Test scores never choose models or recipes.
""")
    code("""import importlib.util, os, subprocess, sys
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
dependencies = {"tensorflow": "tensorflow", "sklearn": "scikit-learn",
                "PIL": "pillow", "matplotlib": "matplotlib"}
missing = [package for module, package in dependencies.items()
           if importlib.util.find_spec(module) is None]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
# Keep Colab's installed TensorFlow/GPU stack; do not upgrade it mid-session.
from pathlib import Path
IN_COLAB = importlib.util.find_spec("google.colab") is not None
""")
    md("""## 1. Settings
The two recipes change several settings together. This compares recipes; it does not
isolate which individual setting caused a difference.

Use **224 pixels** first. A later 320-pixel experiment needs a new run ID and must
finish selection before test evaluation.

Completed stages are reused with identical settings. An interrupted unfinished
stage restarts in a new attempt folder; it does not resume the interrupted epoch.
Drive checkpoints survive a runtime reset.
""")
    code("""SMOKE_TEST = False
USE_DRIVE = True
RUN_ID = "three-models-v1"  # NEW ID if data, settings or TensorFlow/Keras changes.
DRIVE_DATASET_ZIP = "/content/drive/MyDrive/BioGuard/bioguard_comparison_dataset.zip"
LOCAL_DATA_ROOT = None  # Optional local use: extracted comparison-dataset folder.

CONFIG = {
    "seed": 42, "image_size": 224, "batch_size": 32,
    "head_epochs": 12, "fine_epochs": 20,
    "require_gpu": True, "smoke_test": SMOKE_TEST,
    "training_source_sha256": "__SOURCE_HASH__",
}
if SMOKE_TEST:
    CONFIG.update(batch_size=9, head_epochs=1, fine_epochs=1, require_gpu=False)
print("Full comparison: 3 architectures × 2 recipes × 2 training stages."
      if not SMOKE_TEST else "SMOKE TEST ONLY: random weights; not accuracy evidence.")
""".replace("__SOURCE_HASH__", source_hash))
    md("""## 2. Training helpers
This cell supplies the full workflow. No GitHub download, API key or extra Python
file is required. Each exported model includes its appropriate input normalisation.
The app continues supplying float32 RGB pixels in 0–255.
""")
    code(source)
    md("""## 3. Load the frozen dataset
Drive holds checkpoints by default. Grant the normal Drive mount permission when
Colab asks. If the dataset ZIP is missing, this cell offers an upload.
Only use a dataset ZIP you trust. Paths, checksums, labels and split separation are checked.
""")
    code("""if IN_COLAB:
    from google.colab import files
    if USE_DRIVE:
        from google.colab import drive
        drive.mount("/content/drive")
        ZIP_PATH = Path(DRIVE_DATASET_ZIP)
        ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT = Path("/content/drive/MyDrive/BioGuard/experiments") / RUN_ID
    else:
        ZIP_PATH = Path("/content/bioguard_comparison_dataset.zip")
        OUTPUT = Path("/content/bioguard_experiments") / RUN_ID
    if not ZIP_PATH.is_file():
        print("Upload bioguard_comparison_dataset.zip (DATASET, not the model ZIP).")
        uploaded = files.upload()
        names = [name for name in uploaded if name.lower().endswith(".zip")]
        if len(names) != 1:
            raise ValueError("Upload exactly one comparison-dataset ZIP.")
        uploaded_path = Path(names[0])
        if uploaded_path.resolve() != ZIP_PATH.resolve():
            shutil.copy2(uploaded_path, ZIP_PATH)
        del uploaded
    DATA_ROOT = Path(LOCAL_DATA_ROOT) if LOCAL_DATA_ROOT else extract_dataset(
        ZIP_PATH, Path("/content/bioguard_comparison_data"))
else:
    if LOCAL_DATA_ROOT is None:
        raise ValueError("Set LOCAL_DATA_ROOT to an extracted dataset folder for local execution.")
    DATA_ROOT = Path(LOCAL_DATA_ROOT)
    OUTPUT = Path("bioguard_experiments") / RUN_ID
GPUS = tf.config.list_physical_devices("GPU")
for gpu in GPUS:
    tf.config.experimental.set_memory_growth(gpu, True)
print("TensorFlow:", tf.__version__, "Keras:", tf.keras.__version__, "GPU:", GPUS)
print("Outputs:", OUTPUT)
if CONFIG["require_gpu"] and not GPUS:
    raise RuntimeError("Enable a GPU runtime before full training.")
""")
    md("""## 4. Run the experiment
Fine-tuning starts at the best frozen-head checkpoint. Batch Normalization stays
frozen. Augmentation runs only during training. Model, recipe and checkpoint
selection all use **validation macro F1**. No test prediction dataset is built here.
""")
    code("""STATE = compare_models(CONFIG, DATA_ROOT, OUTPUT)
for item in STATE["locked"]["architecture_winners"]:
    print(item["architecture"], item["recipe"]["name"], item["stage"],
          "validation accuracy:", round(item["validation_accuracy"], 4),
          "validation macro F1:", round(item["validation_macro_f1"], 4))
winner = STATE["locked"]["winner"]
print("SELECTED:", winner["architecture"], winner["recipe"]["name"], winner["stage"])
print("Selection is locked. Test results cannot change this selection.")
""")
    md("""## 5. Final historical test comparison
All three architecture winners and the overall winner are already locked.
Evaluate those frozen models, with per-species precision, recall, F1 and confusion matrices.

Do not change the selected model or settings because of these scores. Future training
informed by test mistakes needs a new untouched evaluation set for fresh claims.
Smoke scores cannot be compared with the old **77.89%** result.
""")
    code("""TEST_RESULTS = evaluate_locked_models(STATE)
for item in TEST_RESULTS["models"]:
    print(item["architecture"], "historical-test accuracy:", round(item["accuracy"], 4),
          "macro F1:", round(item["macro_f1"], 4), "photos:", item["test_images"])
print("Prior model historical accuracy:", TEST_RESULTS["historical_baseline"]["test_accuracy"])
print("Test-set status:", TEST_RESULTS["test_set_status"])
draw_results(STATE, TEST_RESULTS)
""")
    md("""## 6. Export and verify the winner
The ZIP uses the app's existing package filenames. Model-specific preprocessing is
embedded. A CPU reload check verifies saved-model inference; its timing is specific
to the computer running this notebook, not your phone/laptop.

The uncertainty threshold is chosen on validation data only. If no threshold meets
the accuracy/coverage rule, it remains unset and predictions require review.
It is not a guarantee of correctness or unknown-species rejection.
""")
    code("""MODEL_ZIP = export_package(STATE, TEST_RESULTS)
print("Selected model package:", MODEL_ZIP)
print("Keep validation_comparison.json and historical_test_comparison.json for the report.")
if IN_COLAB:
    from google.colab import files
    files.download(str(MODEL_ZIP))
""")
    md("""## Bring back
- The downloaded **bioguard_comparison_winner.zip**.
- Validation/test comparison files and recorded environment versions.
- Species with poor recall and representative failures.

The current app/model stays unchanged until a new package is verified and installed.
Image licences and attribution remain in the split manifest. No field pilot,
expert verification or automatic plant-removal approval is claimed.

## References
- [Keras transfer learning and Batch Normalization](https://keras.io/guides/transfer_learning/)
- [MobileNet families](https://keras.io/api/applications/mobilenet/mobilenet_models/)
- [EfficientNetV2 preprocessing](https://keras.io/api/applications/efficientnet_v2/efficientnet_v2_models/)
- [Checkpointing](https://keras.io/api/callbacks/model_checkpoint/)
- [Colab resource FAQ](https://research.google.com/colaboratory/faq.html)
""")
    for index, cell in enumerate(cells):
        cell["id"] = "bioguard-cell-" + str(index)
    notebook = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}, "accelerator": "GPU",
                     "colab": {"name": "BioGuard_Three_Models_Colab.ipynb"}}}
    notebook_path = ROOT / "BioGuard_Three_Models_Colab.ipynb"
    notebook_path.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Notebook:", notebook_path)
    print("Dataset ZIP:", data_zip, "MiB:", round(data_zip.stat().st_size / 1024**2, 1))

if __name__ == "__main__":
    main()
