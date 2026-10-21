"""Authenticated reporting and ecology review, shared by mobile and web."""
from field_clock import field_today
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator, HttpUrl
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from predictor import InvalidPhoto, prepare_image
from records import RecordConflict

LIMIT = 12 * 1024 * 1024
router = APIRouter()


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class Details(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    site: str = Field(min_length=1, max_length=100)
    landmark: str = Field(min_length=1, max_length=200)
    extent: Literal["one", "few", "patch", "unsure"]
    observed_on: date
    notes: str = Field(default="", max_length=1200)
    identify_requested: bool = True
    identification_questioned: bool = False
    site_id: str | None = None
    block_id: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    request_key: str = Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")

    @model_validator(mode="after")
    def valid_date(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Add both coordinates, or leave both empty.")
        if self.observed_on > field_today():
            raise ValueError("Observation date cannot be in the future.")
        return self


class Review(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    revision: int = Field(ge=1)
    decision: Literal["assign", "no_action", "request_info", "cancel", "duplicate", "reopen"]
    work_type: Literal["restoration", "inspection", "removal", "replanting"] = "restoration"
    due_on: date | None = None
    priority: Literal["normal", "high"] = "normal"
    confirmed_species: str = Field(default="", max_length=160)
    confirmed_invasive: bool | None = None
    notes: str = Field(min_length=1, max_length=1600)
    assigned_team_id: str | None = None
    duplicate_of: str | None = None
    removal_instructions: str = Field(default="", max_length=1600)
    replacement_species: str = Field(default="", max_length=160)
    replanting_instructions: str = Field(default="", max_length=1600)
    research_sources: list[HttpUrl] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def assignment_needs_approval(self):
        if self.decision == "assign":
            if not self.assigned_team_id or not self.due_on or self.due_on < field_today():
                raise ValueError("Choose a team and a visit date, today or later.")
            if self.work_type in {"restoration", "removal", "removal_replanting"}:
                if not self.confirmed_species or self.confirmed_species.lower() == "unknown" or self.confirmed_invasive is not True or not self.removal_instructions:
                    raise ValueError("Verify the invasive species and provide removal instructions.")
            if self.work_type in {"restoration", "replanting", "removal_replanting"} and not all((self.replacement_species, self.replanting_instructions)):
                raise ValueError("Choose the replacement species and planting instructions.")
        elif any((self.assigned_team_id, self.removal_instructions, self.replacement_species, self.replanting_instructions)):
            raise ValueError("Work instructions belong to an approved assignment.")
        if self.decision == "duplicate" and not self.duplicate_of:
            raise ValueError("Choose the original report.")
        return self


def token_from(request):
    authorization = request.headers.get("authorization", "")
    return authorization[7:] if authorization.startswith("Bearer ") else request.cookies.get(request.app.state.cookie_name, "")


def user_from(request, role=None):
    user = request.app.state.records.session_user(token_from(request))
    if not user:
        raise HTTPException(401, "Sign in to continue.")
    if user.get("must_change_password") and request.url.path not in {"/auth/me", "/auth/password", "/auth/logout"}:
        raise HTTPException(403, "Change your temporary password before continuing.")
    if role and user["role"] != role:
        raise HTTPException(403, {"management":"This action is for management.","ecology":"This action is for the ecology field team.","ground":"Use a ground-team account."}.get(role,"This account cannot perform this action."))
    return user


async def read_photo(upload):
    if not isinstance(upload, UploadFile):
        raise HTTPException(422, "Add a plant photo.")
    content = await upload.read(LIMIT + 1)
    if not content or len(content) > LIMIT:
        raise HTTPException(413, "Each photo must be between 1 byte and 12 MB.")
    try:
        await run_in_threadpool(prepare_image, content)
        with Image.open(BytesIO(content)) as photo:
            mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(photo.format)
        if not mime:
            raise InvalidPhoto("Choose a JPEG, PNG or WebP photo.")
        return mime, content
    except InvalidPhoto as error:
        raise HTTPException(422, str(error)) from error


@router.post("/auth/login")
async def login(request: Request, details: Login):
    result = await run_in_threadpool(request.app.state.records.login, details.username.strip().lower(), details.password)
    if not result:
        raise HTTPException(401, "Check your username and password. After repeated attempts, wait five minutes.")
    from fastapi.responses import JSONResponse
    response = JSONResponse(result)
    response.set_cookie(request.app.state.cookie_name, result["token"], httponly=True, samesite="strict",
                        secure=os.environ.get("BIOGUARD_SECURE_COOKIES")=="1" or request.url.scheme == "https", max_age=8 * 3600)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/auth/logout")
def logout(request: Request):
    request.app.state.records.logout(token_from(request))
    response = Response(status_code=204)
    response.delete_cookie(request.app.state.cookie_name)
    return response


@router.get("/auth/me")
def me(request: Request):
    return user_from(request)


@router.get("/teams")
def teams(request: Request):
    user_from(request, "management")
    return request.app.state.records.teams()


@router.post("/reports", status_code=201)
async def submit(request: Request):
    user = user_from(request, "ground")
    async with request.form(max_files=2, max_fields=1, max_part_size=LIMIT) as form:
        try:
            details = Details.model_validate_json(form.get("details", ""))
        except (ValidationError, TypeError) as error:
            raise HTTPException(422, "Check the site, landmark, amount and observation date.") from error
        main_mime, content = await read_photo(form.get("photo"))
        photos = [("identification", main_mime, content)]
        if form.get("overview") is not None:
            mime, overview = await read_photo(form["overview"])
            photos.append(("overview", mime, overview))
        metadata = details.model_dump(mode="json")
        request.app.state.records.validate_location(metadata)
        request_key = metadata.pop("request_key")
        digest = sha256(json.dumps(metadata, sort_keys=True).encode() + b"".join(sha256(photo[2]).digest() for photo in photos)).hexdigest()
        prediction = None
        predictor = request.app.state.predictor
        provenance = {"status": "skipped" if not details.identify_requested else "unavailable"}
        # Validate the photo independently; model downtime must not prevent a sighting report.
        if predictor is not None and details.identify_requested:
            async with request.app.state.inference_lock:
                try:
                    prediction = await run_in_threadpool(predictor.predict, content)
                    provenance = {"status": "available", "architecture": predictor.architecture,
                                  "review_threshold": predictor.review_threshold,
                                  "sha256": getattr(predictor, "model_sha256", None)}
                except Exception:
                    provenance = {"status": "unavailable"}
        try:
            return await run_in_threadpool(request.app.state.records.create_report, user, metadata, prediction,
                                          provenance, photos, request_key, digest)
        except RecordConflict as error:
            raise HTTPException(409, str(error)) from error


@router.get("/reports")
def reports(request: Request):
    return request.app.state.records.list_reports(user_from(request))


@router.get("/reports/{identifier}")
def report(identifier: str, request: Request):
    result = request.app.state.records.get_report(identifier, user_from(request))
    if result is None:
        raise HTTPException(404, "Report not found.")
    return result


@router.get("/reports/{identifier}/photos/{photo_id}")
def photo(identifier: str, photo_id: str, request: Request):
    result = request.app.state.records.get_photo(identifier, photo_id, user_from(request))
    if not result:
        raise HTTPException(404, "Photo not found.")
    return Response(content=result[1], media_type=result[0], headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/reports/{identifier}/review")
def review(identifier: str, details: Review, request: Request):
    user = user_from(request, "management")
    try:
        result = request.app.state.records.review_report(identifier, user, details.model_dump(mode="json"))
    except RecordConflict as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if result is None:
        raise HTTPException(404, "Report not found.")
    return result


@router.post("/reports/{identifier}/information")
async def information(identifier: str, request: Request):
    user = user_from(request, "ground")
    async with request.form(max_files=1, max_fields=2, max_part_size=LIMIT) as form:
        notes = form.get("notes", "")
        try:
            revision = int(form.get("revision", ""))
            if not isinstance(notes, str) or len(notes) > 1200:
                raise ValueError()
        except (TypeError, ValueError) as error:
            raise HTTPException(422, "Check your note and refresh the report.") from error
        mime, content = await read_photo(form.get("photo"))
        try:
            result = await run_in_threadpool(request.app.state.records.add_information, identifier, user, content, mime, notes, revision)
        except RecordConflict as error:
            raise HTTPException(409, str(error)) from error
        if result is None:
            raise HTTPException(404, "Report not found.")
        return result


@router.get("/officer", include_in_schema=False)
def officer_page(request: Request):
    response = FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html", headers={"Cache-Control": "no-store"})
    # The native officer WebView supplies its session only on the initial request.
    # Validate it before establishing the HttpOnly cookie used by dashboard requests.
    if request.headers.get("authorization"):
        if not request.headers["authorization"].startswith("Bearer "):
            raise HTTPException(401, "Sign in to continue.")
        user_from(request, "management")
        response.set_cookie(request.app.state.cookie_name, token_from(request), httponly=True, samesite="strict",
                            secure=os.environ.get("BIOGUARD_SECURE_COOKIES")=="1" or request.url.scheme == "https", max_age=8 * 3600)
    else:
        user=request.app.state.records.session_user(token_from(request))
        if not user or user["role"]!="management" or user.get("must_change_password"):
            return RedirectResponse("/",status_code=303,headers={"Cache-Control":"no-store"})
    return response
