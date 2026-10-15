"""In-memory inference with the model package's exact preprocessing."""
from io import BytesIO
import json
from pathlib import Path
import warnings

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_PIXELS = 32_000_000


class InvalidPhoto(ValueError):
    pass


def prepare_image(content: bytes, size: int = 224) -> np.ndarray:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise InvalidPhoto("This photo is too large. Choose a smaller image.")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGB")
                image = ImageOps.pad(
                    image, (size, size), method=Image.Resampling.BILINEAR,
                    color=(0, 0, 0), centering=(0.5, 0.5),
                )
                return np.asarray(image, dtype=np.float32)
    except InvalidPhoto:
        raise
    except (UnidentifiedImageError, OSError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise InvalidPhoto("Choose a readable JPEG, PNG or WebP photo.") from error


class BioGuardPredictor:
    def __init__(self, package_dir: Path):
        # Import at startup, rather than for API/preprocessing tests.
        import tensorflow as tf

        self.classes = json.loads((package_dir / "class_names.json").read_text("utf-8"))
        self.config = json.loads((package_dir / "preprocessing.json").read_text("utf-8"))
        self.selection = json.loads((package_dir / "selection.json").read_text("utf-8"))
        self.policy = json.loads((package_dir / "species_policy.json").read_text("utf-8"))
        self.catalog = json.loads((Path(__file__).parent / "species_catalog.json").read_text("utf-8"))
        for species in self.classes:
            if not self.catalog.get(species, {}).get("common_name"):
                raise ValueError(f"Missing common name for {species}.")
            if not isinstance(self.policy.get(species, {}).get("sdp_invasive"), bool):
                raise ValueError(f"Missing SDP invasive status for {species}.")
        self.architecture = self.config.get("architecture", "MobileNetV2")
        self.review_threshold = self.selection["review_threshold"]
        self.model = tf.keras.models.load_model(package_dir / "bioguard.keras", compile=False)
        if len(self.classes) != self.model.output_shape[-1]:
            raise ValueError("Model output and species labels do not match.")
        # Warm up so the first user's photo doesn't pay the tracing cost.
        self.model(np.zeros((1, self.config["image_size"], self.config["image_size"], 3),
                            dtype=np.float32), training=False)

    def predict(self, content: bytes) -> dict:
        pixels = prepare_image(content, self.config["image_size"])
        probabilities = self.model(pixels[None], training=False).numpy()[0]
        if not np.all(np.isfinite(probabilities)):
            raise RuntimeError("The model returned invalid probabilities.")
        index = int(np.argmax(probabilities))
        confidence = float(probabilities[index])
        threshold = self.review_threshold
        species = self.classes[index]
        return {
            "predicted_species": species,
            "common_name": self.catalog[species]["common_name"],
            "sdp_listed_invasive": self.policy[species]["sdp_invasive"],
            "confidence": confidence,
            "uncertain_identification": threshold is None or confidence < threshold,
            "known_class_scope_only": True,
            "supported_species_count": len(self.classes),
        }
