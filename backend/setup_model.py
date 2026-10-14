"""Extract the supplied package without changing the original ZIP."""
from pathlib import Path
from zipfile import ZipFile
import shutil

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT.parent / "bioguard_model_package.zip"
DESTINATION = ROOT / "model"
REQUIRED = {"bioguard.keras", "class_names.json", "preprocessing.json", "selection.json"}


def extract_package(archive=ARCHIVE, destination=DESTINATION):
    destination = destination.resolve()
    with ZipFile(archive) as package:
        names = set(package.namelist())
        if not REQUIRED.issubset(names):
            raise ValueError("The ZIP is missing required BioGuard model files.")
        for entry in package.infolist():
            target = (destination / entry.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("The ZIP contains an unsafe file path.")
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


if __name__ == "__main__":
    print(f"Model package ready: {extract_package()}")
