"""Offline checks for an explicitly selected local backup; no live model calls."""
import json
import pytest
import restoration_ai as ai
from test_three_roles import roles, auth, sighting
from test_ai_call_budget import DRAFT

@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    for name in ("_last", "_draft_cache", "_user_attempts", "_global_attempts"):
        getattr(ai,name).clear()
    monkeypatch.setenv("GROQ_API_KEY","synthetic-key")
    monkeypatch.setenv("OLLAMA_MODEL","qwen3:8b")
    monkeypatch.setattr(ai,"load_references",lambda c:[{"url":"https://www.nparks.gov.sg/synthetic","title":"Synthetic reference","text":"Grona heterophylla occurs in Malaya."}])

class Response:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,size):return json.dumps({"done":True,"done_reason":"stop","message":{"content":json.dumps({k:v for k,v in DRAFT.items() if k!="candidates"})}}).encode()

def test_selected_backup_uses_one_loopback_request_without_groq_key(monkeypatch):
    calls=[]
    monkeypatch.setattr(ai,"api_key",lambda:pytest.fail("Local backup must not read Groq credentials"))
    def opening(request,**kwargs):calls.append(request);return Response()
    monkeypatch.setattr(ai,"urlopen",opening)
    result=ai.generate({"confirmed_species":"Cleome rutidosperma"},provider="local")
    assert len(calls)==1 and calls[0].full_url=="http://127.0.0.1:11434/api/chat"
    assert calls[0].get_header("Authorization") is None
    payload=json.loads(calls[0].data)
    assert payload["model"]=="qwen3:8b" and payload["stream"] is False
    assert payload["format"]["required"]==list(ai.Draft.model_fields)
    assert result["replacement_species"]=="Grona heterophylla"
    assert result["provider"]=="local"
    assert result["request_receipt"]["groq_requests"]==0
    assert result["request_receipt"]["local_requests"]==1

def test_groq_quota_then_explicit_backup_is_immediate_and_cached(roles,monkeypatch):
    client,app,sessions=roles;report=sighting(client,sessions,key="synthetic_local_backup")
    calls=[]
    def opening(request,**kwargs):
        calls.append(request.full_url)
        if "groq.com" in request.full_url:raise ai.HTTPError(request.full_url,429,"synthetic quota",{},None)
        return Response()
    monkeypatch.setattr(ai,"urlopen",opening)
    path=f"/reports/{report['id']}/restoration-draft"
    payload={"revision":report["revision"],"confirmed_invasive":True,"confirmed_species":"Cleome rutidosperma"}
    failure=client.post(path,headers=auth(sessions,"manager"),json=payload)
    assert failure.status_code==429 and len(calls)==1
    assert failure.headers["x-bioguard-local-backup"]=="available"
    for _ in range(2):
        result=client.post(path,headers=auth(sessions,"manager"),json={**payload,"provider":"local"})
        assert result.status_code==200,result.text
        assert result.json()["provider"]=="local"
    assert len(calls)==2
    receipt=result.json()["request_receipt"]
    assert receipt["cached"] and receipt["groq_requests"]==receipt["local_requests"]==0
    logs=[json.loads(line) for line in (app.state.records.directory/"ai-usage.jsonl").read_text().splitlines()]
    assert [log["groq_requests"] for log in logs]==[1,0,0]
    assert [log["local_requests"] for log in logs]==[0,1,0]
    assert app.state.records.get_report(report["id"],sessions["manager"]["user"])["work_items"]==[]

def test_local_failure_has_no_retry_or_cloud_fallback(monkeypatch):
    calls=[]
    def opening(*args,**kwargs):calls.append(1);raise OSError("synthetic connection refused")
    monkeypatch.setattr(ai,"urlopen",opening)
    with pytest.raises(ai.HTTPException) as error:ai.generate({},provider="local")
    assert len(calls)==1 and "Ollama" in error.value.detail

def test_local_replacement_keeps_source_validation(monkeypatch):
    class Unsupported(Response):
        def read(self,size):return json.dumps({"done":True,"done_reason":"stop","message":{"content":json.dumps({**{k:v for k,v in DRAFT.items() if k!="candidates"},"replacement_species":"Invented plant"})}}).encode()
    monkeypatch.setattr(ai,"urlopen",lambda *a,**k:Unsupported())
    with pytest.raises(ai.HTTPException) as error:ai.generate({},provider="local")
    assert error.value.status_code==502 and "replacement" in error.value.detail

def test_local_still_requires_management_and_confirmation(roles,monkeypatch):
    client,_,sessions=roles;report=sighting(client,sessions,key="synthetic_local_auth")
    monkeypatch.setattr(ai,"urlopen",lambda *a,**k:pytest.fail("Must not call a provider"))
    path=f"/reports/{report['id']}/restoration-draft"
    body={"revision":report["revision"],"confirmed_invasive":True,"provider":"local"}
    assert client.post(path,headers=auth(sessions,"fieldalpha"),json=body).status_code==403
    assert client.post(path,headers=auth(sessions,"manager"),json={**body,"confirmed_invasive":False}).status_code==422


def test_cached_groq_draft_does_not_replace_selected_local_draft(roles,monkeypatch):
    client,_,sessions=roles;report=sighting(client,sessions,key="synthetic_provider_cache")
    calls=[]
    def opening(request,**kwargs):
        calls.append(request.full_url)
        if "groq.com" in request.full_url:
            class GroqResponse(Response):
                def read(self,size):return json.dumps({"choices":[{"finish_reason":"stop","message":{"content":json.dumps(DRAFT)}}]}).encode()
            return GroqResponse()
        return Response()
    monkeypatch.setattr(ai,"urlopen",opening)
    path=f"/reports/{report['id']}/restoration-draft"
    body={"revision":report["revision"],"confirmed_invasive":True,"confirmed_species":"Cleome rutidosperma"}
    cloud=client.post(path,headers=auth(sessions,"manager"),json=body)
    local=client.post(path,headers=auth(sessions,"manager"),json={**body,"provider":"local"})
    assert cloud.status_code==local.status_code==200
    assert cloud.json()["provider"]=="groq" and local.json()["provider"]=="local"
    assert len(calls)==2 and not local.json()["request_receipt"]["cached"]

def test_unconfigured_backup_makes_no_model_request(monkeypatch):
    monkeypatch.setattr(ai,"local_model",lambda:"")
    monkeypatch.setattr(ai,"urlopen",lambda *a,**k:pytest.fail("Must not call a provider"))
    with pytest.raises(ai.HTTPException) as error:ai.generate({},provider="local")
    assert error.value.status_code==503 and "OLLAMA_MODEL" in error.value.detail

def test_truncated_local_output_is_rejected_without_retry(monkeypatch):
    calls=[]
    class Truncated(Response):
        def read(self,size):return json.dumps({"done":True,"done_reason":"length","message":{"content":json.dumps(DRAFT)}}).encode()
    def opening(*a,**k):calls.append(1);return Truncated()
    monkeypatch.setattr(ai,"urlopen",opening)
    with pytest.raises(ai.HTTPException) as error:ai.generate({},provider="local")
    assert error.value.status_code==502 and len(calls)==1


def test_local_replacement_is_constrained_to_retrieved_options(monkeypatch):
    monkeypatch.setattr(ai,"load_references",lambda c:[{"url":"https://www.nparks.gov.sg/synthetic","title":"Synthetic profile","text":"Grona heterophylla native range includes Malaya.","replacement_species":"Grona heterophylla"}])
    calls=[]
    def opening(request,**kwargs):calls.append(json.loads(request.data));return Response()
    monkeypatch.setattr(ai,"urlopen",opening)
    ai.generate({},provider="local")
    assert calls[0]["format"]["properties"]["replacement_species"]["enum"]==["Grona heterophylla"]
