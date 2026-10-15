from io import BytesIO
from pathlib import Path
import sys
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageOps
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app, MAX_UPLOAD_BYTES
from predictor import BioGuardPredictor, InvalidPhoto, prepare_image
from setup_model import ARCHIVE, REQUIRED, ensure_package, extract_package


def photo_bytes(mode="RGB", size=(480, 240), color="green", format="PNG"):
    output = BytesIO()
    Image.new(mode, size, color).save(output, format=format)
    return output.getvalue()


class Predictor:
    classes = ["Mimosa pudica"] * 9
    architecture = "EfficientNetV2B0"
    review_threshold = 0.56

    def predict(self, content):
        prepare_image(content)
        return {
            "predicted_species": "Mimosa pudica", "common_name": "Touch-me-not",
            "sdp_listed_invasive": True, "confidence": 0.81,
            "uncertain_identification": False, "known_class_scope_only": True,
            "supported_species_count": 9,
        }


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Predictor, data_dir=tmp_path, seed_accounts=False)) as api:
        yield api


def test_health_states_no_storage(client):
    assert client.get("/health").json() == {
        "identification_available": True, "status": "ready", "model_architecture": "EfficientNetV2B0",
        "review_threshold": 0.56, "supported_species_count": 9,
        "stores_identification_photos": False, "stores_identification_results": False,
        "stores_submitted_reports": True, "report_storage": "only explicitly submitted reports",
    }


def test_photo_to_identification(client):
    response = client.post("/identify", content=photo_bytes(),
                           headers={"Content-Type": "image/png"})
    assert response.status_code == 200
    assert response.json()["predicted_species"] == "Mimosa pudica"
    assert response.json()["confidence"] == 0.81
    assert response.json()["common_name"] == "Touch-me-not"
    assert response.json()["sdp_listed_invasive"] is True


@pytest.mark.parametrize("content,content_type,status", [
    (b"", "image/jpeg", 400),
    (b"not a photo", "image/jpeg", 422),
    (b"{}", "application/json", 415),
    (b"photo", "video/mp4", 415),
])
def test_invalid_uploads(client, content, content_type, status):
    response = client.post("/identify", content=content, headers={"Content-Type": content_type})
    assert response.status_code == status


def test_size_limit_enforced_with_and_without_content_length(client):
    assert client.post("/identify", content=b"x", headers={
        "Content-Type": "image/jpeg", "Content-Length": str(MAX_UPLOAD_BYTES + 1),
    }).status_code == 413
    # An iterator makes an upload without a declared content length.
    response = client.post("/identify", content=iter([b"x" * (MAX_UPLOAD_BYTES + 1)]),
                           headers={"Content-Type": "image/jpeg"})
    assert response.status_code == 413


def test_exact_package_preprocessing_and_input_range():
    content = photo_bytes(color=(255, 100, 20))
    pixels = prepare_image(content)
    with Image.open(BytesIO(content)) as source:
        expected = np.asarray(ImageOps.pad(
            ImageOps.exif_transpose(source).convert("RGB"), (224, 224),
            method=Image.Resampling.BILINEAR, color=(0, 0, 0), centering=(0.5, 0.5),
        ), dtype=np.float32)
    np.testing.assert_array_equal(pixels, expected)
    assert pixels.shape == (224, 224, 3)
    assert pixels.dtype == np.float32
    assert pixels[112, 112, 0] == 255
    assert np.all(pixels[0] == 0)


def test_exif_orientation_is_applied():
    image = Image.new("RGB", (80, 40), "red")
    exif = image.getexif()
    exif[274] = 6
    output = BytesIO()
    image.save(output, "JPEG", exif=exif)
    pixels = prepare_image(output.getvalue())
    # Rotated portrait image has black side padding, not top padding.
    assert np.all(pixels[:, 0] == 0)
    assert pixels[0, 112, 0] > 240


def test_grayscale_and_alpha_are_converted_to_rgb():
    for mode, color in [("L", 128), ("RGBA", (20, 120, 30, 120))]:
        pixels = prepare_image(photo_bytes(mode=mode, color=color))
        assert pixels.shape == (224, 224, 3)


def test_corrupt_image_is_rejected():
    with pytest.raises(InvalidPhoto):
        prepare_image(b"invalid")


def test_model_exception_returns_a_readable_error(tmp_path):
    class Broken(Predictor):
        def predict(self, content):
            raise RuntimeError("internal details")
    with TestClient(create_app(Broken, data_dir=tmp_path, seed_accounts=False)) as api:
        response = api.post("/identify", content=photo_bytes(),
                            headers={"Content-Type": "image/png"})
    assert response.status_code == 500
    assert "internal details" not in response.text


def test_archive_paths_are_checked_before_any_extraction(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as package:
        for name in REQUIRED:
            package.writestr(name, b"placeholder")
        package.writestr("../outside.txt", b"invalid")
    with pytest.raises(ValueError, match="unsafe"):
        extract_package(archive, tmp_path / "model")
    assert not (tmp_path / "outside.txt").exists()


@pytest.mark.parametrize("confidence,threshold,uncertain", [
    (0.55, 0.56, True), (0.56, 0.56, False), (0.95, 0.56, False), (0.99, None, True),
])
@pytest.mark.parametrize("invasive", [True, False])
def test_prediction_uncertainty_and_species_metadata(confidence, threshold, uncertain, invasive):
    class Prediction:
        def numpy(self):
            return np.array([[confidence, 1 - confidence]], dtype=np.float32)

    model = BioGuardPredictor.__new__(BioGuardPredictor)
    model.classes = ["Mimosa pudica", "Ficus microcarpa"]
    model.config = {"image_size": 224}
    model.review_threshold = threshold
    model.catalog = {"Mimosa pudica": {"common_name": "Touch-me-not"}}
    model.policy = {"Mimosa pudica": {"sdp_invasive": invasive}}
    model.model = lambda pixels, training: Prediction()
    result = model.predict(photo_bytes())
    assert result["uncertain_identification"] is uncertain
    assert result["common_name"] == "Touch-me-not"
    assert result["sdp_listed_invasive"] is invasive
    assert result["known_class_scope_only"] is True


def test_installing_a_changed_package_replaces_the_previous_model(tmp_path):
    destination = tmp_path / "installed"
    archive = tmp_path / "model.zip"
    for model_content in (b"original model", b"new winner"):
        with ZipFile(archive, "w") as package:
            for filename in REQUIRED:
                package.writestr(filename, model_content if filename == "bioguard.keras" else b"{}")
        ensure_package(archive, destination)
        assert (destination / "bioguard.keras").read_bytes() == model_content
    # A missing required file must be repaired even when the archive has not changed.
    (destination / "species_policy.json").unlink()
    ensure_package(archive, destination)
    assert (destination / "species_policy.json").exists()


def test_default_package_is_the_comparison_winner():
    assert ARCHIVE.name == "bioguard_comparison_winner.zip"
