"""Local prototype API. Photos and predictions are never written to disk."""
import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from predictor import BioGuardPredictor, InvalidPhoto

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MODEL_DIR = Path(__file__).resolve().parent / "model"
logger = logging.getLogger("bioguard")


class Identification(BaseModel):
    predicted_species: str
    common_name: str
    sdp_listed_invasive: bool
    confidence: float = Field(ge=0, le=1)
    uncertain_identification: bool
    known_class_scope_only: bool
    supported_species_count: int


def create_app(predictor_factory=None):
    factory = predictor_factory or (lambda: BioGuardPredictor(MODEL_DIR))

    @asynccontextmanager
    async def lifespan(api):
        api.state.predictor = await run_in_threadpool(factory)
        api.state.inference_lock = asyncio.Lock()
        yield
        api.state.predictor = None

    api = FastAPI(title="BioGuard", version="0.1.0", lifespan=lifespan)
    # LAN-only development; permits the Expo browser preview.
    api.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"], allow_credentials=False,
    )

    @api.get("/health")
    def health():
        return {
            "status": "ready",
            "model_architecture": api.state.predictor.architecture,
            "review_threshold": api.state.predictor.review_threshold,
            "supported_species_count": len(api.state.predictor.classes),
            "stores_photos": False,
            "stores_results": False,
        }

    @api.post("/identify", response_model=Identification)
    async def identify(request: Request):
        content_type = request.headers.get("content-type", "").split(";")[0].lower()
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(415, "Choose a JPEG, PNG or WebP photo.")
        length = request.headers.get("content-length")
        if length:
            try:
                declared_length = int(length)
            except ValueError:
                raise HTTPException(400, "Invalid photo upload size.") from None
            if declared_length < 0:
                raise HTTPException(400, "Invalid photo upload size.")
            if declared_length > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Photo is too large. Choose a smaller image.")
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Photo is too large. Choose a smaller image.")
            content.extend(chunk)
        if not content:
            raise HTTPException(400, "Choose a photo first.")
        async with api.state.inference_lock:
            try:
                return await run_in_threadpool(api.state.predictor.predict, bytes(content))
            except InvalidPhoto as error:
                raise HTTPException(422, str(error)) from error
            except Exception:
                logger.exception("Model inference failed")
                raise HTTPException(500, "Could not identify this photo. Please try again.") from None

    return api


app = create_app()
