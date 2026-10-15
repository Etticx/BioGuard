"""Install the selected model package, preserving the source ZIPs."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import shutil

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT.parent / "bioguard_comparison_winner.zip"
DESTINATION = ROOT / "model"
REQUIRED = {"bioguard.keras", "class_names.json", "preprocessing.json", "selection.json",
            "species_policy.json"}


def extract_package(archive=ARCHIVE, destination=DESTINATION):
    archive = Path(archive)
    destination = Path(destination).resolve()
    with ZipFile(archive) as package:
        names = set(package.namelist())
        if not REQUIRED.issubset(names):
            raise ValueError("The ZIP is missing required BioGuard model files.")
        for entry in package.infolist():
            target = (destination / entry.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("The ZIP contains an unsafe file path.")
        damaged = package.testzip()
        if damaged:
            raise ValueError(f"The ZIP contains a damaged file: {damaged}")
        destination.mkdir(parents=True, exist_ok=True)
        for entry in package.infolist():
            target = destination / entry.filename
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(entry) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
    return destination


def ensure_package(archive=ARCHIVE, destination=DESTINATION):
    archive = Path(archive)
    destination = Path(destination)
    digest = sha256(archive.read_bytes()).hexdigest()
    receipt = destination / ".package-sha256"
    if (receipt.exists() and receipt.read_text("utf-8").strip() == digest
            and all((destination / name).is_file() for name in REQUIRED)):
        return destination
    extract_package(archive, destination)
    receipt.write_text(digest + "\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    print(f"Model package ready: {ensure_package()}")
