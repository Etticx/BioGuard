"""Authenticated reporting and ecology review, shared by mobile and web."""
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
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
    request_key: str = Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")

    @model_validator(mode="after")
    def valid_date(self):
        if self.observed_on > date.today():
            raise ValueError("Observation date cannot be in the future.")
        return self


class Review(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    revision: int = Field(ge=1)
    decision: Literal["assign", "no_action", "request_info"]
    confirmed_species: str = Field(default="", max_length=160)
    confirmed_invasive: bool | None = None
    notes: str = Field(min_length=1, max_length=1600)
    assigned_team_id: str | None = None
    removal_instructions: str = Field(default="", max_length=1600)
    replacement_species: str = Field(default="", max_length=160)
    replanting_instructions: str = Field(default="", max_length=1600)

    @model_validator(mode="after")
    def assignment_needs_approval(self):
        if self.decision == "assign":
            if not self.confirmed_species or self.confirmed_species.lower() == "unknown" or self.confirmed_invasive is not True:
                raise ValueError("Confirm an invasive species before approving removal.")
            if not all((self.assigned_team_id, self.removal_instructions, self.replacement_species, self.replanting_instructions)):
                raise ValueError("Choose a team and provide removal and replanting instructions.")
        elif any((self.assigned_team_id, self.removal_instructions, self.replacement_species, self.replanting_instructions)):
            raise ValueError("Work instructions belong to an approved assignment.")
        return self


def token_from(request):
    authorization = request.headers.get("authorization", "")
    return authorization[7:] if authorization.startswith("Bearer ") else request.cookies.get("bioguard_session", "")


def user_from(request, role=None):
    user = request.app.state.records.session_user(token_from(request))
    if not user:
        raise HTTPException(401, "Sign in to continue.")
    if role and user["role"] != role:
        raise HTTPException(403, "This action is for the ecology officer." if role == "officer" else "Use a ground-team account.")
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
    response.set_cookie("bioguard_session", result["token"], httponly=True, samesite="strict",
                        secure=request.url.scheme == "https", max_age=8 * 3600)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/auth/logout")
def logout(request: Request):
    request.app.state.records.logout(token_from(request))
    response = Response(status_code=204)
    response.delete_cookie("bioguard_session")
    return response


@router.get("/auth/me")
def me(request: Request):
    return user_from(request)


@router.get("/teams")
def teams(request: Request):
    user_from(request, "officer")
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
        # The server computes the saved suggestion; clients cannot forge confidence or invasive status.
        async with request.app.state.inference_lock:
            try:
                prediction = await run_in_threadpool(request.app.state.predictor.predict, content)
            except InvalidPhoto as error:
                raise HTTPException(422, str(error)) from error
            except Exception as error:
                raise HTTPException(503, "Identification is unavailable. Your report was not saved; please retry.") from error
        metadata = details.model_dump(mode="json")
        request_key = metadata.pop("request_key")
        digest = sha256(json.dumps(metadata, sort_keys=True).encode() + b"".join(sha256(photo[2]).digest() for photo in photos)).hexdigest()
        predictor = request.app.state.predictor
        provenance = {"architecture": predictor.architecture, "review_threshold": predictor.review_threshold,
                      "sha256": getattr(predictor, "model_sha256", None)}
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
    user = user_from(request, "officer")
    try:
        result = request.app.state.records.review_report(identifier, user, details.model_dump())
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
def officer_page():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html", headers={"Cache-Control": "no-store"})
