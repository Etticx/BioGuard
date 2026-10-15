# First dataset review

Open http://localhost:8084 while Start-Review.ps1 is running.

## What is prepared

Batch 01 contains 30 training photos: eight Cleome rutidosperma, eight Ficus
microcarpa, and two examples of each other species. Photographers are distinct
within each species' sample. This is a small, targeted starting batch, not a
representative estimate of overall dataset quality.

The images are exact copies of original SDHackathon dataset files. No source
photos, labels, dataset splits, model weights or mobile-app files are changed.

## How to review each photo

1. Look at the full image, not only a small thumbnail.
2. Is the intended plant visible, reasonably sharp and the main subject?
3. Is it mostly another plant, a landscape, a person, or an obstruction?
4. Are multiple plants present so that the labelled subject is ambiguous?
5. Can a knowledgeable reviewer support the species label from visible features?
   Open the original observation to inspect its identification context.
6. Choose one status and add a short reason where useful.

- **Photo looks usable**: useful image quality. This does not verify its species.
- **Label needs checking**: species uncertain or possibly wrong. No automatic relabelling.
- **Photo unusable**: the labelled plant cannot reasonably be assessed in this image.
- **Possible duplicate**: another record may show the same image or near-identical view.

If you do not know a species, do not certify it. Flag it for a knowledgeable
reviewer. A model disagreement alone is not evidence that the dataset label is wrong.

Progress is stored in this browser only. Use **Export review decisions** to save
a JSON backup before switching browsers, clearing browser data, or handing off.
These annotations are separate from the mobile app; no prediction history is added.

## Automatic checks

automatic-audit.json records file existence, SHA-256 integrity against the exported
manifest, image decoding, exact duplicates, image dimensions and aspect ratio for
all 2,700 records.

Resolution/aspect-ratio flags are proposed triage rules, not confirmed defects.
Exact hashes do not catch every related image. No flags does not establish a
correct label, useful photo composition, or absence of near duplicates.

## After this batch

Review the flagged photos together. Confirm suspected label changes with a
knowledgeable reviewer, then decide which corrections belong in a new dataset
version. Expand to the remaining training photos in manageable batches.

Keep the existing exported dataset immutable. Review validation photos separately.
Treat inspection of test mistakes as diagnostic work; do not move those images into
training. Future model selection uses validation data and final claims require an
untouched evaluation set.

Do not retrain until review decisions are checked and dataset changes are documented.
