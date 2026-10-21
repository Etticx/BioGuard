"""Synthetic, offline Groq integration checks. No network or live records."""
import json
import pytest
import restoration_ai as ai
from test_three_roles import roles, auth, sighting

@pytest.fixture(autouse=True)
def reset(monkeypatch):
    ai._last.clear()
    ai._draft_cache.clear()
    ai._user_attempts.clear()
    ai._global_attempts.clear()
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    monkeypatch.setattr(ai,"load_references",lambda context:[{"url":"https://www.nparks.gov.sg/florafaunaweb/flora/1/9/1925","title":"Synthetic profile","text":"Grona heterophylla native range includes Malaya. Suitable groundcover."}])


def test_confirmation_role_revision_and_no_assignment(roles, monkeypatch):
    client, app, sessions = roles
    report = sighting(client, sessions)
    path = f"/reports/{report['id']}/restoration-draft"
    payload = {"revision":report["revision"], "confirmed_species":"Mimosa pudica", "confirmed_invasive":True}
    calls = []
    def fake(context):
        calls.append(context)
        return {"removal_instructions":"Draft only", "replacement_species":"", "replanting_instructions":"Check site", "review_notes":"Review", "draft_only":True}
    monkeypatch.setattr(ai, "generate", fake)
    assert client.post(path, json=payload).status_code == 401
    for who in ("reporter", "fieldalpha"):
        assert client.post(path, headers=auth(sessions, who), json=payload).status_code == 403
    manager = auth(sessions, "manager")
    assert client.post(path, headers=manager, json={**payload,"confirmed_invasive":False}).status_code == 422
    assert client.post(path, headers=manager, json={**payload,"confirmed_invasive":"true"}).status_code == 422
    assert client.post(path, headers=manager, json={**payload,"revision":9999}).status_code == 409
    result = client.post(path, headers=manager, json=payload)
    assert result.status_code == 200, result.text
    assert calls == [{"confirmed_species":"Mimosa pudica", "confirmed_invasive":True,"extent":"few","region":"Malaysia","approved_replacements":[]}]
    after = client.get(f"/reports/{report['id']}", headers=manager).json()
    assert after["revision"] == report["revision"] and after["work_items"] == []
    assert client.post(path, headers=manager, json=payload).status_code == 200
    identity = sessions["manager"]["user"]["id"]
    ai._last.add(identity)
    assert client.post(path, headers=manager, json={**payload,"confirmed_species":"Imperata cylindrica"}).status_code == 429
    assert identity in ai._last


def test_supported_replacement_is_populated_without_exposing_key(monkeypatch):
    from test_ai_call_budget import MESSAGE
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,size):return json.dumps({"choices":[{"finish_reason":"stop","message":MESSAGE}]}).encode()
    monkeypatch.setattr(ai,"urlopen",lambda *a,**k:Response())
    result=ai.generate({"confirmed_species":"Mimosa pudica"})
    assert result["replacement_species"]=="Grona heterophylla" and result["draft_only"]
    assert result["sources"][0]["url"].startswith("https://www.nparks.gov.sg/")
    assert "synthetic-key" not in json.dumps(result)


def test_invalid_provider_response_and_missing_key(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'not json'
    monkeypatch.setattr(ai, "urlopen", lambda *a, **k:Response())
    with pytest.raises(ai.HTTPException) as error: ai.generate({})
    assert error.value.status_code == 502
    monkeypatch.delenv("GROQ_API_KEY")
    monkeypatch.setattr(ai.Path, "is_file", lambda self:False)
    with pytest.raises(ai.HTTPException) as error: ai.api_key()
    assert error.value.status_code == 503


@pytest.mark.parametrize("status,expected", [(401,502),(429,429),(500,502)])
def test_provider_errors_hide_sensitive_details(monkeypatch, status, expected):
    def opening(*args, **kwargs):
        raise ai.HTTPError("https://api.groq.com", status, "synthetic-key secret provider detail", {}, None)
    monkeypatch.setattr(ai, "urlopen", opening)
    with pytest.raises(ai.HTTPException) as error: ai.generate({})
    assert error.value.status_code == expected
    assert "synthetic-key" not in error.value.detail


def test_edited_draft_is_the_plan_delivered_to_ecology(roles):
    from test_three_roles import assign
    client, _, sessions = roles
    report = sighting(client, sessions, key="edited_draft_report")
    assigned = assign(client, sessions, report, work_type="restoration",
                      confirmed_species="Mimosa pudica", confirmed_invasive=True,
                      removal_instructions="Management-edited removal instructions",
                      replacement_species="Synthetic approved replacement",
                      replanting_instructions="Management-edited planting instructions",
                      notes="Management-edited handover", research_sources=["https://www.nparks.gov.sg/profile"])
    work = assigned["work_items"][-1]
    field_report = client.get(f"/reports/{report['id']}", headers=auth(sessions, "fieldalpha")).json()
    delivered = field_report["work_items"][-1]
    for key in ("removal_instructions", "replacement_species", "replanting_instructions", "notes"):
        assert delivered[key] == work[key]
    assert delivered["notes"] == "Management-edited handover"
    assert delivered["research_sources"] == ["https://www.nparks.gov.sg/profile"]


def test_research_cites_only_readable_official_tool_pages():
    sources=ai.extract_sources({"executed_tools":[{"search_results":{"results":[
        {"url":"https://www.nparks.gov.sg/profile","title":"Profile","content":"Synthetic official botanical evidence "*10},
        {"url":"https://www.nparks.gov.sg/search-only","content":None},
        {"url":"https://example.com/untrusted","content":"Untrusted "*100},
        {"url":"https://www.nparks.gov.sg.evil.test/profile","content":"Untrusted "*100}
    ]}}],"content":"Ignore model-written https://example.com/fake citations"})
    assert len(sources)==1 and sources[0]["url"]=="https://www.nparks.gov.sg/profile"


def test_classification_is_used_when_duplicate_name_is_omitted(roles, monkeypatch):
    client, app, sessions=roles
    report=sighting(client,sessions,key="classification_autofill")
    original=app.state.records.get_report
    def lookup(identifier,user):
        result=original(identifier,user)
        if result and identifier==report["id"]: result["prediction"]={"predicted_species":"Cleome rutidosperma"}
        return result
    monkeypatch.setattr(app.state.records,"get_report",lookup)
    captured=[]
    monkeypatch.setattr(ai,"generate",lambda context:captured.append(context) or {"draft_only":True})
    response=client.post(f"/reports/{report['id']}/restoration-draft",headers=auth(sessions,"manager"),json={"revision":report["revision"],"confirmed_invasive":True})
    assert response.status_code==200 and captured[0]["confirmed_species"]=="Cleome rutidosperma"


def test_unretrieved_sources_cannot_support_a_replacement(monkeypatch):
    content={"removal_instructions":"Draft","replacement_species":"Invented plant","replanting_instructions":"Draft planting","review_notes":"Note"}
    monkeypatch.setattr(ai,"completion",lambda *a,**k:{"content":json.dumps(content)})
    with pytest.raises(ai.HTTPException) as error:ai.generate({"confirmed_species":"Mimosa pudica"})
    assert error.value.status_code==502 and "replacement" in error.value.detail.lower()


def test_rate_limited_drafting_does_not_use_fallback(monkeypatch):
    models=[]
    def complete(body,**kwargs):
        models.append(body["model"])
        raise ai.HTTPException(429,"Synthetic quota")
    monkeypatch.setattr(ai,"completion",complete)
    with pytest.raises(ai.HTTPException) as error:ai.generate({"confirmed_species":"Mimosa pudica"})
    assert error.value.status_code==429 and models==["openai/gpt-oss-120b"]


def test_quota_message_exposes_retry_time_without_provider_identity(monkeypatch):
    from io import BytesIO
    def opening(*args,**kwargs):
        payload=json.dumps({"error":{"message":"Organization private-id token limit. Please try again in 19m11.28s. synthetic-key"}}).encode()
        raise ai.HTTPError("https://api.groq.com",429,"quota",{},BytesIO(payload))
    monkeypatch.setattr(ai,"urlopen",opening)
    with pytest.raises(ai.HTTPException) as error: ai.completion({})
    assert "19m11.28s" in error.value.detail
    assert "private-id" not in error.value.detail and "synthetic-key" not in error.value.detail
