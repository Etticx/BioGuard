"""Local identification plus explicitly submitted, private sighting reports."""
import asyncio
from contextlib import asynccontextmanager
import logging
import os
import time
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from records import Records
from reporting import router as reporting_router
from workflow_api import router as workflow_router
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


def load_model():
    if os.environ.get("BIOGUARD_MODEL_DISABLED")=="1":
        raise RuntimeError("Model preparation failed; reporting remains available.")
    return BioGuardPredictor(MODEL_DIR)


def create_app(predictor_factory=None, data_dir=None, seed_accounts=True):
    factory = predictor_factory or load_model

    @asynccontextmanager
    async def lifespan(api):
        api.state.records = Records(data_dir or Path(os.environ.get("BIOGUARD_DATA_DIR",str(Path(__file__).parent / "data"))))
        await run_in_threadpool(api.state.records.initialize, seed_accounts)
        api.state.inference_lock = asyncio.Lock()
        try:api.state.predictor = await run_in_threadpool(factory)
        except Exception:
            logger.exception("Identification unavailable; staff reporting remains available")
            api.state.predictor = None
        async def maintenance():
            # Backups include private evidence. No automatic deletion; operators manage retention.
            while True:
                try:
                    existing=list((api.state.records.directory/"backups").glob("backup-*.sqlite3"))
                    if not existing or time.time()-max(p.stat().st_mtime for p in existing)>=86400:
                        await run_in_threadpool(api.state.records.backup_database)
                except Exception:logger.exception("Scheduled backup failed")
                await asyncio.sleep(60)
        task=asyncio.create_task(maintenance()) if data_dir is None else None
        try:yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):await task
            api.state.predictor=None

    api = FastAPI(title="BioGuard", version="0.2.0", lifespan=lifespan)
    # LAN-only development; permits the Expo browser preview.
    api.add_middleware(
        CORSMiddleware, allow_origins=os.environ.get("BIOGUARD_CORS_ORIGINS","*").split(","), allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept", "Authorization"], allow_credentials=False,
    )

    @api.middleware("http")
    async def limit_and_private(request, call_next):
        if request.method == "POST":
            origin=request.headers.get("origin")
            # Browser cookie writes must come from this origin. Native bearer requests do not use cookies.
            if request.cookies.get("bioguard_session") and not request.headers.get("authorization") and origin:
                from urllib.parse import urlsplit
                if urlsplit(origin).netloc != request.headers.get("host"):
                    return JSONResponse({"detail":"Use the BioGuard page for this action."},status_code=403)
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
    api.include_router(workflow_router)
    api.mount("/officer-assets", StaticFiles(directory=Path(__file__).parent.parent / "web"), name="officer-assets")

    @api.get("/health")
    def health():
        return {
            "status": "ready",
            "model_architecture": api.state.predictor.architecture if api.state.predictor else None,
            "identification_available": api.state.predictor is not None,
            "review_threshold": api.state.predictor.review_threshold if api.state.predictor else None,
            "supported_species_count": len(api.state.predictor.classes) if api.state.predictor else 0,
            "stores_identification_photos": False,
            "stores_identification_results": False,
            "stores_submitted_reports": True,
            "report_storage": "only explicitly submitted reports",
        }

    @api.post("/identify", response_model=Identification)
    async def identify(request: Request):
        if api.state.predictor is None:
            raise HTTPException(503,"Identification is unavailable. You can still send a sighting report for officer review.")
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

    mobile_dist=Path(__file__).parent.parent/"mobile"/"dist"
    if mobile_dist.is_dir():
        from fastapi.responses import FileResponse
        @api.get("/",include_in_schema=False)
        @api.get("/team",include_in_schema=False)
        @api.get("/report",include_in_schema=False)
        @api.get("/drafts",include_in_schema=False)
        @api.get("/updates",include_in_schema=False)
        def mobile_page():return FileResponse(mobile_dist/"index.html")
        if (mobile_dist/"_expo").is_dir():api.mount("/_expo",StaticFiles(directory=mobile_dist/"_expo"),name="expo-assets")
        if (mobile_dist/"assets").is_dir():api.mount("/assets",StaticFiles(directory=mobile_dist/"assets"),name="mobile-assets")
    return api


app = create_app()
