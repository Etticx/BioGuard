"""Execute three architectures without downloading pretrained weights."""
import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "2")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
os.environ.setdefault("MPLBACKEND", "Agg")
import json
from pathlib import Path
import sys
import training

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
WORK = ROOT / "verification"
WORK.mkdir(exist_ok=True)
BUNDLE = training.extract_dataset(ROOT / "bioguard_comparison_dataset.zip", WORK / "dataset")
config = {
    "seed": 42, "image_size": 224, "batch_size": 9,
    "head_epochs": 1, "fine_epochs": 1, "require_gpu": False, "smoke_test": True,
    "training_source_sha256": training.file_sha(ROOT / "training.py"),
}
state = training.compare_models(config, BUNDLE, WORK / "smoke_run")
results = training.evaluate_locked_models(state)
training.draw_results(state, results)
archive = training.export_package(state, results)
assert len(results["models"]) == 3
assert len(state["validation_results"]) == 6
assert results["run_type"] == "smoke_test_only"
assert all(row["test_images"] == 9 for row in results["models"])
sys.path.insert(0, str(PROJECT / "backend"))
from predictor import BioGuardPredictor
predictor = BioGuardPredictor(archive.parent / "SMOKE_TEST_ONLY_model_package")
photo = BUNDLE / state["val_rows"][0]["relative_path"]
prediction = predictor.predict(photo.read_bytes())
assert prediction["supported_species_count"] == 9
assert 0 <= prediction["confidence"] <= 1
print(json.dumps({
    "architectures_executed": list(training.ARCHITECTURES),
    "training_stages_executed": 6, "cpu_export_reload_passed": True,
    "existing_app_predictor_passed": True, "smoke_archive": str(archive),
    "real_accuracy_claim": False,
}, indent=2))
