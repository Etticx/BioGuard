"""Synthetic, offline Groq integration checks. No network or live records."""
import json
import pytest
import restoration_ai as ai
from test_three_roles import roles, auth, sighting

@pytest.fixture(autouse=True)
def reset(monkeypatch):
    ai._last.clear()
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")


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
    assert client.post(path, headers=manager, json=payload).status_code == 429
    assert identity in ai._last


def test_groq_schema_private_key_and_unapproved_replacement(monkeypatch):
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            return json.dumps({"choices":[{"finish_reason":"stop","message":{"content":json.dumps({"removal_instructions":"Review first", "replacement_species":"Invented approval", "replanting_instructions":"Check site", "review_notes":"Draft"})}}]}).encode()
    def opening(request, timeout):
        captured.update(json.loads(request.data))
        assert request.full_url == "https://api.groq.com/openai/v1/chat/completions"
        assert timeout == 35
        assert request.get_header("User-agent") == "BioGuard/0.2"
        return Response()
    monkeypatch.setattr(ai, "urlopen", opening)
    result = ai.generate({"confirmed_species":"Mimosa pudica"})
    assert captured["response_format"]["json_schema"]["strict"] is True
    assert captured["model"] == "openai/gpt-oss-120b"
    assert result["replacement_species"] == "" and result["draft_only"]
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
                      notes="Management-edited handover")
    work = assigned["work_items"][-1]
    field_report = client.get(f"/reports/{report['id']}", headers=auth(sessions, "fieldalpha")).json()
    delivered = field_report["work_items"][-1]
    for key in ("removal_instructions", "replacement_species", "replanting_instructions", "notes"):
        assert delivered[key] == work[key]
    assert delivered["notes"] == "Management-edited handover"
