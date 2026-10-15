"""Local identification plus explicitly submitted, private sighting reports."""
import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from records import Records
from reporting import router as reporting_router
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


def create_app(predictor_factory=None, data_dir=None, seed_accounts=True):
    factory = predictor_factory or (lambda: BioGuardPredictor(MODEL_DIR))

    @asynccontextmanager
    async def lifespan(api):
        api.state.predictor = await run_in_threadpool(factory)
        api.state.inference_lock = asyncio.Lock()
        api.state.records = Records(data_dir or Path(__file__).parent / "data")
        await run_in_threadpool(api.state.records.initialize, seed_accounts)
        yield
        api.state.predictor = None

    api = FastAPI(title="BioGuard", version="0.1.0", lifespan=lifespan)
    # LAN-only development; permits the Expo browser preview.
    api.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept", "Authorization"], allow_credentials=False,
    )

    @api.middleware("http")
    async def limit_and_private(request, call_next):
        if request.method == "POST":
            # Bound the complete request, including both report photos and multipart overhead.
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > 25 * 1024 * 1024:
                    return JSONResponse({"detail": "Upload is too large."}, status_code=413)
                body.extend(chunk)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    api.include_router(reporting_router)
    api.mount("/officer-assets", StaticFiles(directory=Path(__file__).parent.parent / "web"), name="officer-assets")

    @api.get("/health")
    def health():
        return {
            "status": "ready",
            "model_architecture": api.state.predictor.architecture,
            "review_threshold": api.state.predictor.review_threshold,
            "supported_species_count": len(api.state.predictor.classes),
            "stores_identification_photos": False,
            "stores_identification_results": False,
            "stores_submitted_reports": True,
            "report_storage": "only explicitly submitted reports",
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
