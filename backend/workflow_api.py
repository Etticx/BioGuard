"""Role-protected visit evidence, verification and pilot administration."""
from field_clock import field_today
from datetime import date
from hashlib import sha256
import json
import re
import secrets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator, ValidationError
from typing import Literal
from starlette.concurrency import run_in_threadpool
from reporting import user_from, read_photo, LIMIT, Review
from records import RecordConflict

router=APIRouter()
class Strict(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra="forbid")
class Progress(Strict):
    revision:int=Field(ge=1)
    action:Literal["start","blocked"]
    notes:str=Field(default="",max_length=1600)
    @model_validator(mode="after")
    def reason(self):
        if self.action=="blocked" and not self.notes:raise ValueError("Describe the problem.")
        return self
class Completion(Strict):
    revision:int=Field(ge=1)
    request_key:str=Field(min_length=8,max_length=100,pattern=r"^[a-zA-Z0-9_-]+$")
    stage:Literal["removal","replanting","both","observation"]
    observed_on:date
    notes:str=Field(min_length=1,max_length=1600)
    removal_complete:bool=False
    removed_on:date|None=None
    planted_on:date|None=None
    planted_species:str=Field(default="",max_length=160)
    quantity:int|None=Field(default=None,ge=1,le=100000)
    regrowth:Literal["yes","no","unknown"]|None=None
    surviving_count:int|None=Field(default=None,ge=0,le=100000)
    checked_count:int|None=Field(default=None,ge=1,le=100000)
    @model_validator(mode="after")
    def dates(self):
        if any(value and value>field_today() for value in (self.observed_on,self.removed_on,self.planted_on)):raise ValueError("Evidence dates must be today or earlier.")
        if any(value and value>self.observed_on for value in (self.removed_on,self.planted_on)):raise ValueError("Visit date must be on or after the recorded work dates.")
        if self.removed_on and self.planted_on and self.planted_on<self.removed_on:raise ValueError("Planting cannot precede removal.")
        if (self.surviving_count is None)!=(self.checked_count is None):raise ValueError("Record both surviving and checked plants.")
        if self.checked_count and self.surviving_count>self.checked_count:raise ValueError("Surviving plants cannot exceed plants checked.")
        return self
class Verification(Strict):
    revision:int=Field(ge=1)
    decision:Literal["accept","corrections","reopen"]
    notes:str=Field(min_length=1,max_length=1600)
    next_visit_on:date|None=None
    assigned_team_id:str|None=None
    no_followup_reason:str=Field(default="",max_length=1600)
    @model_validator(mode="after")
    def next_date(self):
        if self.next_visit_on and self.next_visit_on<field_today():raise ValueError("Schedule the next visit today or later.")
        if self.decision!="accept" and (self.next_visit_on or self.assigned_team_id or self.no_followup_reason):raise ValueError("Next-visit fields belong to acceptance only.")
        if self.assigned_team_id and not self.next_visit_on:raise ValueError("Choose a next visit date with the team.")
        return self
class Password(Strict):
    # Passwords must be hashed exactly as entered, just as they are at login.
    model_config=ConfigDict(str_strip_whitespace=False,extra="forbid")
    current_password:str=Field(min_length=1,max_length=200)
    new_password:str=Field(min_length=10,max_length=200)
class NewUser(Strict):
    username:str=Field(min_length=2,max_length=80,pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name:str=Field(min_length=1,max_length=100)
    role:Literal["ground","officer"]
    team_id:str|None=None
class Active(Strict):active:bool
class CatalogEntry(Strict):
    name:str=Field(min_length=1,max_length=100)
    site_id:str|None=None

def invoke(method,*args):
    try:result=method(*args)
    except RecordConflict as error:raise HTTPException(409,str(error)) from error
    except ValueError as error:raise HTTPException(422,str(error)) from error
    if result is None or result is False:raise HTTPException(404,"Record not found.")
    return result

@router.post("/reports/{identifier}/work/{work_id}/progress")
def progress(identifier:str,work_id:str,details:Progress,request:Request):
    user=user_from(request,"ground")
    return invoke(request.app.state.records.progress_work,identifier,work_id,user,details.revision,details.action,details.notes)

@router.post("/reports/{identifier}/work/{work_id}/revise")
def revise(identifier:str,work_id:str,details:Review,request:Request):
    user=user_from(request,"officer")
    if details.decision!="assign":raise HTTPException(422,"Choose assignment to revise a visit.")
    return invoke(request.app.state.records.revise_work,identifier,work_id,user,details.revision,details.model_dump(mode="json"))

@router.post("/reports/{identifier}/work/{work_id}/complete")
async def complete(identifier:str,work_id:str,request:Request):
    user=user_from(request,"ground")
    async with request.form(max_files=2,max_fields=1,max_part_size=LIMIT) as form:
        try:details=Completion.model_validate_json(form.get("details",""))
        except (ValidationError,TypeError) as error:raise HTTPException(422,"Check the evidence dates, stage, counts and note.") from error
        photos=[await read_photo(form.get("photo"))]
        if form.get("overview") is not None:photos.append(await read_photo(form["overview"]))
        values=details.model_dump(mode="json")
        digest=sha256(json.dumps(values,sort_keys=True).encode()+b"".join(sha256(photo[1]).digest() for photo in photos)).hexdigest()
        return await run_in_threadpool(invoke,request.app.state.records.complete_work,identifier,work_id,user,values,photos,digest)

@router.post("/reports/{identifier}/work/{work_id}/verify")
def verify(identifier:str,work_id:str,details:Verification,request:Request):
    user=user_from(request,"officer")
    return invoke(request.app.state.records.verify_work,identifier,work_id,user,details.model_dump(mode="json"))

@router.get("/notifications")
def notifications(request:Request):return request.app.state.records.notifications(user_from(request))
@router.post("/notifications/{identifier}/read",status_code=204)
def read_notice(identifier:str,request:Request):
    invoke(request.app.state.records.mark_notice,identifier,user_from(request))
    return Response(status_code=204)
@router.get("/catalog")
def catalog(request:Request):
    user_from(request)
    return request.app.state.records.catalog()
@router.get("/reports/{identifier}/duplicates")
def duplicates(identifier:str,request:Request):return request.app.state.records.duplicate_candidates(identifier,user_from(request,"officer"))
@router.post("/auth/password",status_code=204)
def password(details:Password,request:Request):
    user=user_from(request)
    try:request.app.state.records.change_password(user,details.current_password,details.new_password)
    except ValueError as error:raise HTTPException(422,str(error)) from error
    response=Response(status_code=204);response.delete_cookie(request.app.state.cookie_name);return response
@router.get("/admin/users")
def users(request:Request):
    user_from(request,"officer");return request.app.state.records.admin_users()
@router.post("/admin/users",status_code=201)
def add_user(details:NewUser,request:Request):
    actor=user_from(request,"officer");temporary=secrets.token_urlsafe(15)
    if details.role=="ground" and not details.team_id:raise HTTPException(422,"Choose a team for this staff member.")
    identifier=invoke(request.app.state.records.add_user,details.username,temporary,details.display_name,details.role,details.team_id,True)
    request.app.state.records.audit(actor,"user_created",identifier)
    return {"id":identifier,"temporary_password":temporary}
@router.post("/admin/users/{identifier}/reset")
def reset(identifier:str,request:Request):return {"temporary_password":invoke(request.app.state.records.reset_user,user_from(request,"officer"),identifier)}
@router.post("/admin/users/{identifier}/active",status_code=204)
def active_user(identifier:str,details:Active,request:Request):
    invoke(request.app.state.records.set_user_active,user_from(request,"officer"),identifier,details.active);return Response(status_code=204)
@router.post("/admin/catalog/{kind}",status_code=201)
def add_catalog(kind:str,details:CatalogEntry,request:Request):return invoke(request.app.state.records.add_catalog,user_from(request,"officer"),kind,details.name,details.site_id)
@router.post("/admin/catalog/{kind}/{identifier}/active",status_code=204)
def active_catalog(kind:str,identifier:str,details:Active,request:Request):
    invoke(request.app.state.records.set_catalog_active,user_from(request,"officer"),kind,identifier,details.active);return Response(status_code=204)
@router.get("/admin/catalog")
def admin_catalog(request:Request):
    user_from(request,"officer")
    with request.app.state.records.connect() as db:return {kind:[dict(row) for row in db.execute(f"SELECT * FROM {kind} ORDER BY name")] for kind in ("teams","sites","blocks")}
@router.get("/admin/audit")
def audit(request:Request):
    user_from(request,"officer")
    with request.app.state.records.connect() as db:return [dict(row) for row in db.execute("SELECT * FROM admin_audit ORDER BY created_at DESC LIMIT 200")]
@router.post("/admin/backups",status_code=201)
def backup(request:Request):
    actor=user_from(request,"officer");result=request.app.state.records.backup_database();request.app.state.records.audit(actor,"backup_created",result["name"]);return result
@router.get("/admin/backups")
def backups(request:Request):
    user_from(request,"officer");folder=request.app.state.records.directory/"backups"
    return [{"name":p.name,"bytes":p.stat().st_size} for p in sorted(folder.glob("backup-*.sqlite3"),reverse=True)] if folder.exists() else []
@router.get("/admin/backups/{name}")
def download(name:str,request:Request):
    actor=user_from(request,"officer")
    if not re.fullmatch(r"backup-[a-zA-Z0-9-]+\.sqlite3",name):raise HTTPException(404,"Backup not found.")
    target=request.app.state.records.directory/"backups"/name
    if not target.is_file():raise HTTPException(404,"Backup not found.")
    request.app.state.records.audit(actor,"backup_downloaded",name)
    return FileResponse(target,filename=name,media_type="application/octet-stream",headers={"Cache-Control":"no-store"})
