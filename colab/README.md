# BioGuard three-model Colab experiment

Combines step 3 (architectures) and step 4 (training improvements).
The notebook is prepared; full training still needs to run in Colab.

## Files to use

- **BioGuard_Three_Models_Colab.ipynb** — self-contained notebook.
- **bioguard_comparison_dataset.zip** — original 2,700 photos, their licences and attribution,
  frozen 1,951 / 369 / 380 train/validation/test split, and baseline metadata.
  This DATASET ZIP is different from the original model ZIP.

## Start in Colab

1. Open https://colab.research.google.com/ and choose **File → Upload notebook**.
2. Select BioGuard_Three_Models_Colab.ipynb.
3. Upload bioguard_comparison_dataset.zip to **My Drive / BioGuard**.
4. Choose **Runtime → Change runtime type → T4 GPU**, or another available GPU.
5. Keep SMOKE_TEST=False and USE_DRIVE=True, then run the cells in order.
6. Download the winning model ZIP when finished.

If the ZIP is absent from Drive, the loading cell offers a direct upload.
Drive preserves completed stages through a runtime reset. An interrupted
unfinished stage restarts; completed stages are reused.

## What runs

Three architectures: MobileNetV2, MobileNetV3 Large, EfficientNetV2-B0.
Two recipes per architecture, each with frozen-head training then fine-tuning.

Recipes vary dropout, head/fine-tuning learning rates and the fraction of the
backbone unfrozen. Augmentation, epoch budgets and splits are shared. Batch
Normalization stays frozen; early stopping and ReduceLROnPlateau are enabled.
The best validation macro-F1 checkpoint is saved.

First comparison: 224-pixel images. A later resolution experiment needs a new run ID.
Six trials with up to 12 head and 20 fine-tuning epochs can require substantial
GPU time. No fixed runtime or GPU availability is promised.

## Interpretation

- Choose the model/recipe/stage using validation data only.
- All architecture winners are locked before historical test evaluation.
- The test images were already inspected. Their results are a historical
  benchmark, not a new untouched field evaluation.
- Photo review is unfinished; no review decisions were silently applied.
- Further training informed by test mistakes needs a new untouched evaluation set.
- Smoke mode uses random weights and tiny subsets to check code only.

## Outputs

The winner ZIP follows the existing app package format and includes the model,
class order, preprocessing, review threshold, comparison metrics, per-class test
metrics, attribution, training logs and runtime versions. A CPU reload check verifies
saved-model inference. Bring the ZIP back before replacing the current app model.

## Resuming

Reuse a run ID only with identical code, data, settings and TensorFlow/Keras versions.
The fingerprint prevents mixing incompatible runs. New settings need a new run ID.
Completed checkpoints are integrity checked; interrupted attempts are retained.

Internal training.py and prepare_colab.py regenerate the notebook and data bundle.
The training code is embedded in the notebook, so no extra Python upload is needed.

## Local verification performed

- Notebook schema and every code cell pass validation/parsing.
- Dataset ZIP CRC checks pass; all 2,700 source images and licences are present.
- All three architectures complete one frozen-head and one fine-tuning smoke epoch.
- Validation selection, locked historical-test evaluation, plotting and package export run.
- The selected smoke package reloads on CPU and works with the existing app predictor.
- These use tiny subsets and random initial weights. They do not establish improved accuracy.
- The full pretrained GPU comparison has not been run.
