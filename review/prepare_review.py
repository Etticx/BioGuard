"""Read-only audit of source photos; prepare a separate manual-review batch."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import shutil

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SOURCE = PROJECT.parent / "SDHackathon" / "data" / "bioguard"
MANIFEST = PROJECT / "backend" / "model" / "split_manifest.jsonl"
WEAK_SPECIES = {"Cleome rutidosperma", "Ficus microcarpa"}


def main():
    records = [json.loads(line) for line in MANIFEST.read_text("utf-8").splitlines() if line.strip()]
    issues = []
    hashes = defaultdict(list)
    audited = []
    for record in records:
        source = (SOURCE / record["relative_path"]).resolve()
        if not source.is_relative_to(SOURCE.resolve()):
            raise ValueError("Manifest path leaves the source dataset.")
        flags = []
        actual_sha = None
        width = height = None
        if not source.is_file():
            flags.append("missing_file")
        else:
            actual_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            hashes[actual_sha].append(record["photo_id"])
            if actual_sha != record["sha256"]:
                flags.append("manifest_hash_mismatch")
            try:
                with Image.open(source) as image:
                    image.load()
                    oriented = ImageOps.exif_transpose(image)
                    width, height = oriented.size
                    if max(width, height) < 224:
                        flags.append("below_model_input_resolution")
                    if min(width, height) < 96:
                        flags.append("very_short_image_side")
                    if max(width, height) / min(width, height) > 3:
                        flags.append("extreme_aspect_ratio")
            except (OSError, ValueError, Image.DecompressionBombError):
                flags.append("unreadable_image")
        item = {
            **record,
            "review_flags": flags,
            "actual_width": width,
            "actual_height": height,
            "actual_sha256": actual_sha,
        }
        audited.append(item)
    duplicates = [ids for ids in hashes.values() if len(ids) > 1]
    duplicated_ids = {photo_id for group in duplicates for photo_id in group}
    for item in audited:
        if item["photo_id"] in duplicated_ids:
            item["review_flags"].append("exact_duplicate")
        if item["review_flags"]:
            issues.append({
                "photo_id": item["photo_id"], "species": item["species"],
                "split": item["split"], "flags": item["review_flags"],
                "relative_path": item["relative_path"],
            })
    # Start with training photos. Validation/test photos do not enter this batch.
    species_order = ["Cleome rutidosperma", "Ficus microcarpa"] + [
        species for species in dict.fromkeys(row["species"] for row in records)
        if species not in WEAK_SPECIES
    ]
    batch = []
    for species in species_order:
        candidates = [row for row in audited if row["split"] == "train" and row["species"] == species]
        random.Random(42).shuffle(candidates)
        candidates.sort(key=lambda row: len(row["review_flags"]), reverse=True)
        count = 8 if species in WEAK_SPECIES else 2
        chosen = []
        observers = set()
        for row in candidates:
            if row["observer_id"] in observers:
                continue
            chosen.append(row)
            observers.add(row["observer_id"])
            if len(chosen) == count:
                break
        if len(chosen) != count:
            raise ValueError("Not enough distinct photographers for the planned batch.")
        batch.extend(chosen)
    photos = ROOT / "photos"
    photos.mkdir(exist_ok=True)
    review_items = []
    for row in batch:
        source = SOURCE / row["relative_path"]
        target = photos / (str(row["photo_id"]) + source.suffix.lower())
        # Copy exact originals; never crop, relabel, move or delete dataset photos.
        if source.is_file():
            shutil.copy2(source, target)
        review_items.append({
            "photo_id": str(row["photo_id"]),
            "expected_species": row["species"],
            "split": row["split"],
            "observer_id": str(row["observer_id"]),
            "observation_id": str(row["observation_id"]),
            "image": "photos/" + target.name,
            "observation_url": row["observation_url"],
            "source_url": row["source_url"],
            "photo_license": row["photo_license"],
            "attribution": row["attribution"],
            "width": row["actual_width"],
            "height": row["actual_height"],
            "sha256": row["actual_sha256"],
            "flags": row["review_flags"],
            "review_status": "unreviewed",
            "label_verification": "not_expert_verified",
        })
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": str(SOURCE),
        "source_manifest": str(MANIFEST),
        "total_images": len(records),
        "split_counts": dict(Counter(row["split"] for row in records)),
        "flag_counts": dict(Counter(flag for row in audited for flag in row["review_flags"])),
        "exact_duplicate_groups": duplicates,
        "issues": issues,
        "manual_reviews_completed_by_this_script": 0,
        "botanical_labels_expert_verified_by_this_script": 0,
        "batch_size": len(batch),
        "batch_species_counts": dict(Counter(row["species"] for row in batch)),
        "notes": [
            "Flags are review prompts, not automatic exclusion decisions.",
            "Small-size and aspect-ratio cutoffs are proposed triage rules.",
            "Exact hashes do not detect every near duplicate.",
            "This audit does not establish correct species labels.",
            "The manual batch contains training images only.",
            "Source photos, labels, splits, model and mobile app are unchanged.",
        ],
    }
    (ROOT / "automatic-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (ROOT / "batch-01.json").write_text(json.dumps(review_items, indent=2), encoding="utf-8")
    payload = json.dumps(review_items, ensure_ascii=True).replace("</", "<\\/")
    template = (ROOT / "review.template.html").read_text("utf-8")
    (ROOT / "index.html").write_text(template.replace("__REVIEW_DATA__", payload), encoding="utf-8")
    print(json.dumps({
        "audited_images": report["total_images"], "flag_counts": report["flag_counts"],
        "exact_duplicate_groups": len(duplicates), "manual_batch_size": len(batch),
        "manual_reviews_completed": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
