"""Three-role contracts; all accounts, images and databases here are synthetic."""
import json
import pytest
from fastapi.testclient import TestClient
from test_api import Predictor, photo_bytes
from app import create_app
from field_clock import field_today
from records import Records

PASSWORD = "synthetic-three-role-password"

@pytest.fixture
def roles(tmp_path):
    api = create_app(Predictor, data_dir=tmp_path, seed_accounts=False, private_beta=True)
    with TestClient(api) as client:
        sessions = {}
        for username, role in (("reporter", "ground"), ("otherreporter", "ground"),
                               ("fieldalpha", "ecology"), ("fieldbeta", "ecology"),
                               ("manager", "management")):
            api.state.records.add_user(username, PASSWORD, "Synthetic " + username, role)
            response = client.post("/auth/login", json={"username": username, "password": PASSWORD})
            assert response.status_code == 200, response.text
            sessions[username] = response.json()
            client.cookies.clear()
        yield client, api, sessions


def auth(sessions, username):
    return {"Authorization": "Bearer " + sessions[username]["token"]}


def sighting(client, sessions, key="three_role_report", username="reporter"):
    response = client.post("/reports", headers=auth(sessions, username),
        data={"details": json.dumps({"site": "Synthetic block", "landmark": "Synthetic test drain",
              "extent": "few", "observed_on": str(field_today()), "notes": "Synthetic test sighting",
              "request_key": key, "identify_requested": False})},
        files={"photo": ("synthetic.jpg", photo_bytes(format="JPEG"), "image/jpeg")})
    assert response.status_code == 201, response.text
    return response.json()


def plan(report, team, **change):
    return {"revision": report["revision"], "decision": "assign", "work_type": "inspection",
            "due_on": str(field_today()), "confirmed_species": "Unknown", "confirmed_invasive": None,
            "notes": "Synthetic inspection instructions", "assigned_team_id": team,
            "removal_instructions": "", "replacement_species": "", "replanting_instructions": "", **change}


def assign(client, sessions, report, **change):
    team = sessions["fieldalpha"]["user"]["team_id"]
    response = client.post(f"/reports/{report['id']}/review", headers=auth(sessions, "manager"),
                           json=plan(report, team, **change))
    assert response.status_code == 200, response.text
    return response.json()


def progress(client, sessions, report, action="accept", username="fieldalpha", revision=None):
    work = report["work_items"][-1]
    return client.post(f"/reports/{report['id']}/work/{work['id']}/progress", headers=auth(sessions, username),
                       json={"revision": work["revision"] if revision is None else revision,
                             "action": action, "notes": "Synthetic progress note"})


def evidence(client, sessions, report, username="fieldalpha", **change):
    work = report["work_items"][-1]
    details = {"revision": work["revision"], "request_key": "three_role_evidence", "stage": "observation",
               "observed_on": str(field_today()), "notes": "Synthetic inspection observation",
               "removal_complete": False, "suggested_species": "Leucaena leucocephala",
               "recommended_action": "removal", "removal_recommendation": "Synthetic site-specific removal proposal",
               "replacement_recommendation": "Synthetic replacement proposal", **change}
    return client.post(f"/reports/{report['id']}/work/{work['id']}/complete", headers=auth(sessions, username),
        data={"details": json.dumps(details)},
        files={"photo": ("synthetic-evidence.jpg", photo_bytes(format="JPEG", size=(24, 32)), "image/jpeg")})


def verify(client, sessions, report, username="manager", **change):
    work = report["work_items"][-1]
    return client.post(f"/reports/{report['id']}/work/{work['id']}/verify", headers=auth(sessions, username),
                       json={"revision": work["revision"], "decision": "accept",
                             "notes": "Synthetic management verification", **change})


def test_three_roles_have_distinct_sessions_and_management_entry(roles):
    client, _, sessions = roles
    for username, role in (("reporter", "ground"), ("fieldalpha", "ecology"), ("manager", "management")):
        headers = auth(sessions, username)
        assert client.get("/auth/me", headers=headers).json()["role"] == role
        assert client.get("/admin/users", headers=headers).status_code == (200 if role == "management" else 403)
        response = client.get("/officer", headers=headers)
        assert response.status_code == (200 if role == "management" else 403)
        if role == "management":
            assert "HttpOnly" in response.headers["set-cookie"]
            assert "SameSite=strict" in response.headers["set-cookie"]
            assert sessions[username]["token"] not in response.text
        else:
            assert "set-cookie" not in response.headers
        client.cookies.clear()
    assert client.post("/auth/logout", headers=auth(sessions, "fieldalpha")).status_code == 204
    assert client.get("/auth/me", headers=auth(sessions, "fieldalpha")).status_code == 401


@pytest.mark.parametrize("role", ["ground", "ecology", "management"])
def test_temporary_password_is_required_before_any_workspace(roles, role):
    client, api, _ = roles
    api.state.records.add_user("temporary", PASSWORD, "Synthetic temporary", role, must_change=True)
    login = client.post("/auth/login", json={"username": "temporary", "password": PASSWORD})
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"]
    old = {"Authorization": "Bearer " + login.json()["token"]}
    client.cookies.clear()
    assert client.get("/reports", headers=old).status_code == 403
    assert client.get("/officer", headers=old).status_code == 403
    assert client.post("/auth/password", headers=old,
                       json={"current_password": PASSWORD, "new_password": "synthetic-replacement-password"}).status_code == 204
    assert client.get("/auth/me", headers=old).status_code == 401
    fresh = client.post("/auth/login", json={"username": "temporary", "password": "synthetic-replacement-password"})
    assert fresh.status_code == 200 and fresh.json()["user"]["role"] == role
    assert not fresh.json()["user"]["must_change_password"]


def test_only_ground_reports_and_only_management_assigns_ecology_teams(roles):
    client, _, sessions = roles
    report = sighting(client, sessions)
    team = sessions["fieldalpha"]["user"]["team_id"]
    for username in ("fieldalpha", "manager"):
        response = client.post("/reports", headers=auth(sessions, username), data={}, files={})
        assert response.status_code == 403
    for username in ("reporter", "fieldalpha"):
        assert client.post(f"/reports/{report['id']}/review", headers=auth(sessions, username),
                           json=plan(report, team)).status_code == 403
    listed = client.get("/teams", headers=auth(sessions, "manager"))
    assert listed.status_code == 200
    assert {row["id"] for row in listed.json()} == {sessions[name]["user"]["team_id"] for name in ("fieldalpha", "fieldbeta")}
    wrong = sessions["reporter"]["user"]["team_id"]
    assert client.post(f"/reports/{report['id']}/review", headers=auth(sessions, "manager"),
                       json=plan(report, wrong)).status_code == 422
    assign(client, sessions, report)


def test_assignment_rejects_a_team_without_active_ecology_members(roles):
    client, _, sessions = roles
    target = sessions["fieldbeta"]["user"]
    assert client.post(f"/admin/users/{target['id']}/active", headers=auth(sessions, "manager"),
                       json={"active": False}).status_code == 204
    report = sighting(client, sessions)
    response = client.post(f"/reports/{report['id']}/review", headers=auth(sessions, "manager"),
                           json=plan(report, target["team_id"]))
    assert response.status_code == 422
    assert target["team_id"] not in {row["id"] for row in client.get("/teams", headers=auth(sessions, "manager")).json()}


def test_ecology_must_accept_and_only_its_assigned_team_can_progress(roles):
    client, _, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    assert progress(client, sessions, report, "start").status_code == 409
    assert evidence(client, sessions, report).status_code == 409
    assert progress(client, sessions, report, username="reporter").status_code == 403
    assert progress(client, sessions, report, username="manager").status_code == 403
    assert progress(client, sessions, report, username="fieldbeta").status_code == 404
    assert client.get(f"/reports/{report['id']}", headers=auth(sessions, "fieldbeta")).status_code == 404
    response = progress(client, sessions, report)
    assert response.status_code == 200, response.text
    accepted = response.json()
    assert accepted["work_items"][-1]["status"] == "accepted"
    assert progress(client, sessions, accepted, "start", revision=report["work_items"][-1]["revision"]).status_code == 409
    started = progress(client, sessions, accepted, "start")
    assert started.status_code == 200, started.text
    assert started.json()["work_items"][-1]["status"] == "in_progress"


def test_inspection_evidence_is_idempotent_private_and_management_closes_without_followup(roles):
    client, _, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    accepted = progress(client, sessions, report).json()
    response = evidence(client, sessions, accepted)
    assert response.status_code == 200, response.text
    awaiting = response.json()
    work = awaiting["work_items"][-1]
    assert awaiting["status"] == "awaiting_verification"
    assert work["completions"][-1]["recommended_action"] == "removal"
    assert len(work["completions"]) == 1
    assert not awaiting["review"]["confirmed_invasive"]
    retried = evidence(client, sessions, accepted)
    assert retried.status_code == 200 and len(retried.json()["work_items"][-1]["completions"]) == 1
    assert evidence(client, sessions, accepted, notes="Changed synthetic payload").status_code == 409
    evidence_photo = next(item for item in awaiting["photos"] if item.get("work_id"))
    for username in ("reporter", "otherreporter", "fieldbeta"):
        assert client.get(evidence_photo["url"], headers=auth(sessions, username)).status_code == 404
    ground_view = client.get(f"/reports/{report['id']}", headers=auth(sessions, "reporter")).json()
    assert ground_view["work_items"] == []
    assert "Synthetic inspection observation" not in json.dumps(ground_view)
    assert ground_view["notes"] == "Synthetic test sighting"
    assert all(not item.get("work_id") for item in ground_view["photos"])
    assert client.get(evidence_photo["url"], headers=auth(sessions, "fieldalpha")).status_code == 200
    assert verify(client, sessions, awaiting, username="fieldalpha").status_code == 403
    assert verify(client, sessions, awaiting, username="reporter").status_code == 403
    closed = verify(client, sessions, awaiting)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "completed"
    assert len(closed.json()["work_items"]) == 1
    assert closed.json()["work_items"][-1]["status"] == "verified"


@pytest.mark.parametrize("missing", ["suggested_species", "recommended_action"])
def test_inspection_requires_an_observation_and_recommendation(roles, missing):
    client, _, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    accepted = progress(client, sessions, report).json()
    value = "" if missing == "suggested_species" else None
    response = evidence(client, sessions, accepted, **{missing: value})
    assert response.status_code == 422


def test_inspection_recommendation_cannot_bypass_management_removal_confirmation(roles):
    client, _, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    accepted = progress(client, sessions, report).json()
    awaiting = evidence(client, sessions, accepted).json()
    reopened = verify(client, sessions, awaiting, decision="reopen")
    assert reopened.status_code == 200, reopened.text
    report = reopened.json()
    team = sessions["fieldalpha"]["user"]["team_id"]
    unsafe = plan(report, team, work_type="removal", removal_instructions="Synthetic instructions",
                  confirmed_species="Leucaena leucocephala", confirmed_invasive=None)
    assert client.post(f"/reports/{report['id']}/review", headers=auth(sessions, "fieldalpha"), json={**unsafe, "confirmed_invasive": True}).status_code == 403
    assert client.post(f"/reports/{report['id']}/review", headers=auth(sessions, "manager"), json=unsafe).status_code == 422
    approved = assign(client, sessions, report, work_type="removal", confirmed_species="Leucaena leucocephala",
                      confirmed_invasive=True, removal_instructions="Synthetic management-approved instructions")
    accepted = progress(client, sessions, approved).json()
    response = evidence(client, sessions, accepted, request_key="approved_removal_evidence", stage="removal",
                        removed_on=str(field_today()), removal_complete=True)
    assert response.status_code == 200, response.text
    closed = verify(client, sessions, response.json())
    assert closed.status_code == 200 and closed.json()["status"] == "completed"
    assert len(closed.json()["work_items"]) == 2


@pytest.mark.parametrize("legacy", ["monitoring", "removal_replanting", "follow_up"])
def test_legacy_work_types_cannot_be_assigned_as_new_work(roles, legacy):
    client, _, sessions = roles
    report = sighting(client, sessions)
    team = sessions["fieldalpha"]["user"]["team_id"]
    response = client.post(f"/reports/{report['id']}/review", headers=auth(sessions, "manager"),
                           json=plan(report, team, work_type=legacy))
    assert response.status_code == 422
    assert client.get(f"/reports/{report['id']}", headers=auth(sessions, "manager")).json()["revision"] == report["revision"]


def test_reassignment_removes_previous_ecology_team_access(roles):
    client, _, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    work = report["work_items"][-1]
    revised = client.post(f"/reports/{report['id']}/work/{work['id']}/revise", headers=auth(sessions, "manager"),
        json=plan({"revision": work["revision"]}, sessions["fieldbeta"]["user"]["team_id"]))
    assert revised.status_code == 200, revised.text
    assert client.get(f"/reports/{report['id']}", headers=auth(sessions, "fieldalpha")).status_code == 404
    assert progress(client, sessions, revised.json(), username="fieldalpha").status_code == 404
    assert progress(client, sessions, revised.json(), username="fieldbeta").status_code == 200


def test_migration_preserves_legacy_officer_identity_sessions_and_historical_work(roles):
    client, api, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    work = report["work_items"][-1]
    manager_id = sessions["manager"]["user"]["id"]
    ground_team = sessions["reporter"]["user"]["team_id"]
    with api.state.records.connect() as db:
        data = json.loads(db.execute("SELECT data FROM work_items WHERE id=?", (work["id"],)).fetchone()[0])
        data["work_type"] = "removal_replanting"
        db.execute("UPDATE users SET role='officer' WHERE id=?", (manager_id,))
        db.execute("UPDATE work_items SET team_id=?,data=? WHERE id=?", (ground_team, json.dumps(data), work["id"]))
        db.execute("UPDATE reports SET assigned_group_id=? WHERE id=?", (ground_team, report["id"]))
        api.state.records.emit(db, "synthetic_legacy_notice", report["id"], "Synthetic legacy management notice", role="officer")
        photo_before = bytes(db.execute("SELECT content FROM photos WHERE report_id=?", (report["id"],)).fetchone()[0])
    migrated = Records(api.state.records.directory)
    migrated.initialize(seed=False)
    migrated.initialize(seed=False)
    me = client.get("/auth/me", headers=auth(sessions, "manager"))
    assert me.status_code == 200 and me.json()["id"] == manager_id and me.json()["role"] == "management"
    assert any(item["message"] == "Synthetic legacy management notice" for item in client.get("/notifications", headers=auth(sessions, "manager")).json())
    restored = client.get(f"/reports/{report['id']}", headers=auth(sessions, "manager"))
    assert restored.status_code == 200
    assert restored.json()["work_items"][-1]["id"] == work["id"]
    assert restored.json()["work_items"][-1]["work_type"] == "removal_replanting"
    assert restored.json()["work_items"][-1]["legacy"] is True
    assert restored.json()["work_items"][-1]["requires_reassignment"] is True
    assert client.get(restored.json()["photos"][0]["url"], headers=auth(sessions, "manager")).content == photo_before
    assert progress(client, sessions, restored.json(), username="reporter").status_code == 403
    with migrated.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM users WHERE username='manager'").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM work_items WHERE report_id=?", (report["id"],)).fetchone()[0] == 1


def test_last_ecology_member_cannot_be_disabled_even_with_a_ground_legacy_teammate(roles):
    client, api, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    field = sessions["fieldalpha"]["user"]
    # A historical mixed team must not make a ground reporter count as a field worker.
    with api.state.records.connect() as db:
        db.execute("UPDATE users SET team_id=? WHERE id=?", (field["team_id"], sessions["otherreporter"]["user"]["id"]))
    response = client.post(f"/admin/users/{field['id']}/active", headers=auth(sessions, "manager"), json={"active": False})
    assert response.status_code == 422
    assert progress(client, sessions, report, username="otherreporter").status_code == 403
    assert client.get("/auth/me", headers=auth(sessions, "fieldalpha")).status_code == 200


def test_failed_next_assignment_rolls_back_verification_and_valid_next_plan_is_atomic(roles):
    client, api, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    accepted = progress(client, sessions, report).json()
    awaiting = evidence(client, sessions, accepted).json()
    team = sessions["fieldalpha"]["user"]["team_id"]
    next_plan = plan(awaiting, team, work_type="removal", confirmed_species="Leucaena leucocephala",
                     confirmed_invasive=True, removal_instructions="Synthetic management approval")
    assert verify(client, sessions, awaiting, next_plan={**next_plan, "revision": awaiting["revision"] - 1}).status_code == 409
    inactive = sessions["fieldbeta"]["user"]["team_id"]
    with api.state.records.connect() as db:
        db.execute("UPDATE teams SET active=0 WHERE id=?", (inactive,))
    failed = verify(client, sessions, awaiting, next_plan={**next_plan, "assigned_team_id": inactive})
    assert failed.status_code == 422
    unchanged = client.get(f"/reports/{report['id']}", headers=auth(sessions, "manager")).json()
    assert unchanged["revision"] == awaiting["revision"]
    assert unchanged["work_items"][-1]["status"] == "awaiting_verification"
    assert unchanged["work_items"][-1]["verification"] is None
    assert len(unchanged["work_items"]) == 1
    approved = verify(client, sessions, awaiting, next_plan=next_plan)
    assert approved.status_code == 200, approved.text
    result = approved.json()
    assert result["status"] == "assigned" and len(result["work_items"]) == 2
    assert result["work_items"][0]["status"] == "verified"
    assert result["work_items"][-1]["work_type"] == "removal"
    assert result["review"]["confirmed_invasive"] is True
    assert len(result["photos"]) == len(awaiting["photos"])


def test_historical_and_current_ecology_teams_only_receive_their_own_job_evidence(roles):
    client, _, sessions = roles
    report = assign(client, sessions, sighting(client, sessions))
    accepted = progress(client, sessions, report).json()
    inspection = evidence(client, sessions, accepted, notes="Synthetic private alpha inspection").json()
    alpha_photo = next(item for item in inspection["photos"] if item.get("work_id"))
    beta_plan = plan(inspection, sessions["fieldbeta"]["user"]["team_id"], work_type="removal",
                     confirmed_species="Leucaena leucocephala", confirmed_invasive=True,
                     removal_instructions="Synthetic private beta removal plan", notes="Synthetic private beta instructions")
    assigned = verify(client, sessions, inspection, next_plan=beta_plan)
    assert assigned.status_code == 200, assigned.text
    accepted_beta = progress(client, sessions, assigned.json(), username="fieldbeta")
    assert accepted_beta.status_code == 200, accepted_beta.text
    response = evidence(client, sessions, accepted_beta.json(), username="fieldbeta", request_key="synthetic_beta_evidence",
                        stage="removal", removal_complete=True, removed_on=str(field_today()),
                        notes="Synthetic private beta completion")
    assert response.status_code == 200, response.text
    beta_work_id = response.json()["work_items"][-1]["id"]
    beta_photo = next(item for item in response.json()["photos"] if item.get("work_id") == beta_work_id)
    alpha = client.get(f"/reports/{report['id']}", headers=auth(sessions, "fieldalpha"))
    assert alpha.status_code == 200
    assert len(alpha.json()["work_items"]) == 1 and alpha.json()["work_items"][0]["work_type"] == "inspection"
    assert alpha.json()["review"] is None
    assert "Synthetic private beta" not in json.dumps(alpha.json())
    beta = client.get(f"/reports/{report['id']}", headers=auth(sessions, "fieldbeta"))
    assert beta.status_code == 200 and len(beta.json()["work_items"]) == 1
    assert "Synthetic private alpha inspection" not in json.dumps(beta.json())
    assert client.get(alpha_photo["url"], headers=auth(sessions, "fieldbeta")).status_code == 404
    assert client.get(beta_photo["url"], headers=auth(sessions, "fieldalpha")).status_code == 404
    manager = client.get(f"/reports/{report['id']}", headers=auth(sessions, "manager"))
    assert manager.status_code == 200 and len(manager.json()["work_items"]) == 2
    ground = client.get(f"/reports/{report['id']}", headers=auth(sessions, "reporter"))
    assert ground.status_code == 200 and ground.json()["work_items"] == []
    assert "Synthetic private alpha inspection" not in ground.text
    assert "Synthetic private beta" not in ground.text
    assert ground.json()["notes"] == "Synthetic test sighting"
