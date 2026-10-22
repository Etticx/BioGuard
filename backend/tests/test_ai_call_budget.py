"""Offline contract: one provider request, complete draft, cached repeats, local limits."""
import json
import pytest
import restoration_ai as ai
from test_three_roles import roles, auth, sighting

DRAFT={"removal_instructions":"1. Remove as reviewed.\n2. Contain material.\n3. Take an after-removal photo.",
       "replacement_species":"Grona heterophylla", "replanting_instructions":"1. Check sun and drainage.\n2. Plant the proposed groundcover if approved.\n3. Record planting and photo.",
       "review_notes":"Proposed replacement requires management site approval.", "candidates":[]}
MESSAGE={"content":json.dumps(DRAFT),"executed_tools":[{"name":"browser.open","search_results":{"results":[
    {"title":"Synthetic botanical profile","url":"https://www.nparks.gov.sg/florafaunaweb/flora/1/9/1925",
     "content":"Synthetic fixture: Grona heterophylla native distribution includes Malaya. A groundcover for full sun with suitable drainage. "*3}]}}]}

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY","synthetic-key")
    monkeypatch.setattr(ai,"load_references",lambda context:[{"id":1,"url":"https://www.nparks.gov.sg/florafaunaweb/flora/1/9/1925","title":"Synthetic profile","text":"Grona heterophylla native distribution includes Malaya. Groundcover for full sun and suitable drainage."}],raising=False)
    for name in ("_last","_draft_cache","_user_attempts","_global_attempts"):
        value=getattr(ai,name,None)
        if value is not None: value.clear()


def test_all_four_sections_use_one_provider_request(monkeypatch):
    calls=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,size):return json.dumps({"choices":[{"finish_reason":"stop","message":MESSAGE}]}).encode()
    def opening(request,**kwargs):calls.append(json.loads(request.data));return Response()
    monkeypatch.setattr(ai,"urlopen",opening)
    result=ai.generate({"confirmed_species":"Cleome rutidosperma","extent":"few"})
    assert len(calls)==1
    assert "inspection_brief" not in calls[0]["response_format"]["json_schema"]["schema"]["required"]
    assert "tools" not in calls[0] and "tool_choice" not in calls[0]
    assert calls[0]["response_format"]["type"]=="json_schema"
    assert all(result[key] for key in ("removal_instructions","replacement_species","replanting_instructions","review_notes"))
    assert result["replacement_species"]=="Grona heterophylla"
    assert result["request_receipt"]["groq_requests"]==1
    assert result["request_receipt"]["pipeline"]=="inspection-independent-v5"


def test_quota_error_never_triggers_fallback_or_second_request(monkeypatch):
    calls=[]
    def opening(*args,**kwargs):calls.append(1);raise ai.HTTPError("https://api.groq.com",429,"quota",{},None)
    monkeypatch.setattr(ai,"urlopen",opening)
    with pytest.raises(ai.HTTPException) as error:ai.generate({"confirmed_species":"Cleome rutidosperma"})
    assert error.value.status_code==429 and len(calls)==1


def test_duplicate_report_draft_is_cached_without_new_generation(roles,monkeypatch):
    client,_,sessions=roles;report=sighting(client,sessions,key="budget_cached_report")
    calls=[]
    monkeypatch.setattr(ai,"generate",lambda context:calls.append(context) or {**DRAFT,"draft_only":True})
    path=f"/reports/{report['id']}/restoration-draft";payload={"revision":report["revision"],"confirmed_species":"Cleome rutidosperma","confirmed_invasive":True}
    first=client.post(path,headers=auth(sessions,"manager"),json=payload)
    second=client.post(path,headers=auth(sessions,"manager"),json=payload)
    assert first.status_code==second.status_code==200
    assert len(calls)==1
    for key in ("removal_instructions","replacement_species","replanting_instructions","review_notes"):
        assert first.json()[key]==second.json()[key]
    assert first.json()["request_receipt"]["cached"] is False
    assert second.json()["request_receipt"]["cached"] is True
    assert second.json()["request_receipt"]["groq_requests"]==0


def test_fast_different_report_is_limited_before_provider_call(roles,monkeypatch):
    client,_,sessions=roles
    reports=[sighting(client,sessions,key="budget_rate_report_"+str(i)) for i in range(2)]
    calls=[]
    monkeypatch.setattr(ai,"generate",lambda context:calls.append(context) or {**DRAFT,"draft_only":True})
    results=[client.post(f"/reports/{r['id']}/restoration-draft",headers=auth(sessions,"manager"),json={"revision":r["revision"],"confirmed_species":"Cleome rutidosperma","confirmed_invasive":True}) for r in reports]
    assert results[0].status_code==200 and results[1].status_code==429
    assert int(results[1].headers["retry-after"])>0 and len(calls)==1


def test_later_replacement_source_is_not_lost_after_removal_references(monkeypatch):
    from copy import deepcopy
    message=deepcopy(MESSAGE)
    pages=message["executed_tools"][0]["search_results"]["results"]
    pages[:0]=[{"url":"https://www.nparks.gov.sg/removal/"+str(i),"content":"Synthetic removal guidance only "*10} for i in range(5)]
    monkeypatch.setattr(ai,"completion",lambda *a,**k:message)
    result=ai.generate({"confirmed_species":"Cleome rutidosperma"})
    assert result["replacement_species"]=="Grona heterophylla"


def test_management_account_hourly_cap_blocks_even_after_cooldown(roles,monkeypatch):
    client,_,sessions=roles;report=sighting(client,sessions,key="hourly_budget_report")
    clock=[10000.0];monkeypatch.setattr(ai,"monotonic",lambda:clock[0])
    calls=[];monkeypatch.setattr(ai,"generate",lambda context:calls.append(context) or {**DRAFT,"draft_only":True})
    for index in range(11):
        response=client.post(f"/reports/{report['id']}/restoration-draft",headers=auth(sessions,"manager"),json={"revision":report["revision"],"confirmed_species":"Synthetic species "+str(index),"confirmed_invasive":True})
        assert response.status_code==(200 if index<10 else 429)
        clock[0]+=31
    assert len(calls)==10


def test_failed_attempt_is_rate_limited_without_automatic_retry(roles,monkeypatch):
    client,_,sessions=roles;report=sighting(client,sessions,key="failed_budget_report")
    calls=[]
    def fail(context):calls.append(context);raise ai.HTTPException(502,"Synthetic provider failure")
    monkeypatch.setattr(ai,"generate",fail)
    statuses=[client.post(f"/reports/{report['id']}/restoration-draft",headers=auth(sessions,"manager"),json={"revision":report["revision"],"confirmed_species":"Cleome rutidosperma","confirmed_invasive":True}).status_code for _ in range(2)]
    assert statuses==[502,429] and len(calls)==1


def test_inline_numbering_is_normalized_without_splitting_decimals(monkeypatch):
    message={"content":json.dumps({**DRAFT,"removal_instructions":"1. Wear gloves. 2. Pull carefully; retain a 2.5 cm sample. 3. Bag fragments.","replanting_instructions":"1) Check the site. 2) Plant if approved. 3) Take a photo."})}
    monkeypatch.setattr(ai,"completion",lambda *a,**k:message)
    result=ai.generate({"confirmed_species":"Cleome rutidosperma"})
    assert result["removal_instructions"]=="1. Wear gloves.\n2. Pull carefully; retain a 2.5 cm sample.\n3. Bag fragments."
    assert result["replanting_instructions"]=="1. Check the site.\n2. Plant if approved.\n3. Take a photo."


def test_actual_transport_receipt_and_cached_receipt_are_audited(roles,monkeypatch):
    client,app,sessions=roles;report=sighting(client,sessions,key="transport_receipt_report")
    calls=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,size):return json.dumps({"id":"chatcmpl-synthetic-receipt","choices":[{"finish_reason":"stop","message":{"content":json.dumps(DRAFT)}}]}).encode()
    def opening(request,**kwargs):calls.append(json.loads(request.data));return Response()
    monkeypatch.setattr(ai,"urlopen",opening)
    path=f"/reports/{report['id']}/restoration-draft";payload={"revision":report["revision"],"confirmed_species":"Cleome rutidosperma","confirmed_invasive":True}
    receipts=[client.post(path,headers=auth(sessions,"manager"),json=payload).json()["request_receipt"] for _ in range(2)]
    assert [r["groq_requests"] for r in receipts]==[1,0] and len(calls)==1
    assert receipts[0]["provider_request_id"]=="chatcmpl-synthetic-receipt"
    logs=[json.loads(line) for line in (app.state.records.directory/"ai-usage.jsonl").read_text().splitlines()]
    assert [log["groq_requests"] for log in logs]==[1,0]
    assert "synthetic-key" not in json.dumps(logs)
