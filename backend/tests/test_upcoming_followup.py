"""Post-restoration follow-up contracts; disposable accounts, photos and databases only."""
import json
from datetime import timedelta
import pytest
from field_clock import field_today
from test_api import photo_bytes
from test_reporting import setup, submit, assignment
from test_workflow import review, accept, verify
from test_restoration import evidence


def ready(setup, days_ago=0):
    client, ground, management, _, team, _, ecology, _ = setup
    report = submit(client, ground, location_mode="osm", map_id="elmina-lakeside-v1",
                    latitude=3.180661, longitude=101.509091).json()
    report = accept(client, ecology, review(client, management, report, team, work_type="restoration"))
    actual = str(field_today() - timedelta(days=days_ago))
    response = evidence(setup, report, removed_on=actual, planted_on=actual)
    assert response.status_code == 200, response.text
    return response.json()


def approved(setup, **change):
    client, _, management, *_ = setup
    report = ready(setup)
    response = verify(client, management, report, **change)
    assert response.status_code == 200, response.text
    return response.json()


def followup(report):
    items = [item for item in report["work_items"] if item.get("followup_of")]
    assert len(items) == 1
    return items[0]


def findings(setup, report, who=None, two=False, **change):
    client, _, _, _, _, _, ecology, _ = setup
    work = followup(report)
    body = {"revision": work["revision"], "request_key": "synthetic_followup_findings",
            "stage": "observation", "observed_on": str(field_today()),
            "notes": "Synthetic follow-up visit observation.", "regrowth": "no",
            "replacement_condition": "healthy", "other_invasive": "no",
            "suggested_species": work["confirmed_species"], "recommended_action": "none", **change}
    files = {"photo": ("synthetic-current.jpg", photo_bytes(format="JPEG"), "image/jpeg")}
    if two:
        files["overview"] = ("synthetic-additional.jpg", photo_bytes(format="JPEG", color="blue"), "image/jpeg")
    return client.post(f"/reports/{report['id']}/work/{work['id']}/complete",
                       headers=who or ecology, data={"details": json.dumps(body)}, files=files)


def test_approval_creates_one_linked_inspection_preserving_location_and_evidence(setup):
    client, _, management, _, team, _, ecology, other_ecology = setup
    report = ready(setup)
    old = report["work_items"][-1]
    assert not any(w.get("followup_of") for w in report["work_items"])
    response = verify(client, management, report)
    assert response.status_code == 200, response.text
    updated = response.json()
    work = followup(updated)
    assert updated["status"] != "completed"
    assert work["work_type"] == "inspection" and work["status"] == "assigned"
    assert work["team_id"] == team and work["previous_work_id"] == old["id"]
    assert work["followup_of"] == old["id"] and not work["legacy"]
    assert work["due_on"] == str(field_today() + timedelta(days=14))
    assert work["confirmed_species"] == old["confirmed_species"]
    saved = work["restoration_snapshot"]
    assert saved["point"]["latitude"] == report["latitude"]
    assert saved["point"]["longitude"] == report["longitude"]
    assert saved["completions"] == old["completions"]
    assert saved["planted_species"] == old["replacement_species"]
    delivered = client.get("/reports/" + report["id"], headers=ecology)
    assert delivered.status_code == 200
    assert followup(delivered.json())["restoration_snapshot"] == saved
    for photo_id in saved["completions"][-1]["photo_ids"]:
        url = next(p["url"] for p in delivered.json()["photos"] if p["id"] == photo_id)
        assert client.get(url, headers=ecology).status_code == 200
        assert client.get(url, headers=other_ecology).status_code == 404
    # Retrying a stale approval may conflict, but must never create another ticket.
    retry = verify(client, management, report)
    assert retry.status_code in {200, 409}
    latest = client.get("/reports/" + report["id"], headers=management).json()
    assert len([w for w in latest["work_items"] if w.get("followup_of")]) == 1


def test_default_due_date_uses_actual_planting_even_if_already_overdue(setup):
    client, _, management, *_ = setup
    report = ready(setup, days_ago=21)
    result = verify(client, management, report)
    assert result.status_code == 200, result.text
    work = followup(result.json())
    assert work["due_on"] == str(field_today() - timedelta(days=7))
    assert work["overdue"] is True


def test_management_can_override_default_inspection_date(setup):
    expected = str(field_today() + timedelta(days=23))
    assert followup(approved(setup, next_visit_on=expected))["due_on"] == expected


def test_pending_planting_and_requested_corrections_create_no_followup(setup):
    from test_restoration import assigned
    client, _, management, *_ = setup
    report = assigned(setup)
    partial = evidence(setup, report, stage="removal").json()
    assert verify(client, management, partial).status_code == 409
    assert len(partial["work_items"]) == 1
    done = evidence(setup, partial, stage="replanting", key="synthetic_finish_planting").json()
    corrected = verify(client, management, done, decision="corrections")
    assert corrected.status_code == 200, corrected.text
    assert not any(w.get("followup_of") for w in corrected.json()["work_items"])


def test_followup_findings_are_team_scoped_and_wait_for_management_review(setup):
    client, ground, management, _, _, _, ecology, other_ecology = setup
    report = approved(setup)
    assert findings(setup, report).status_code == 409
    report = accept(client, ecology, report)
    assert findings(setup, report, who=ground).status_code == 403
    assert findings(setup, report, who=other_ecology).status_code == 404
    result = findings(setup, report)
    assert result.status_code == 200, result.text
    awaiting = result.json()
    assert followup(awaiting)["status"] == "awaiting_verification"
    assert awaiting["status"] != "completed"
    retried = findings(setup, report)
    assert retried.status_code == 200
    assert len(followup(retried.json())["completions"]) == 1
    assert verify(client, ecology, awaiting).status_code == 403
    closed = verify(client, management, awaiting)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "completed"
    assert len(closed.json()["work_items"]) == 2


@pytest.mark.parametrize("change", [{"regrowth": None}, {"replacement_condition": None}, {"other_invasive": None},
                                   {"other_invasive": "yes"}])
def test_followup_requires_all_findings_and_extra_plant_pin_and_photo(setup, change):
    client, _, _, _, _, _, ecology, _ = setup
    report = accept(client, ecology, approved(setup))
    assert findings(setup, report, **change).status_code == 422


@pytest.mark.parametrize("change", [{"regrowth": "yes"}, {"regrowth": "unknown"},
                                   {"replacement_condition": "dead"}, {"replacement_condition": "struggling"}])
def test_problematic_findings_cannot_close_without_corrective_assignment(setup, change):
    client, _, management, _, team, _, ecology, _ = setup
    report = accept(client, ecology, approved(setup))
    response = findings(setup, report, **change)
    assert response.status_code == 200, response.text
    report = response.json()
    assert verify(client, management, report).status_code == 422
    corrected = verify(client, management, report, decision="corrections")
    assert corrected.status_code == 200, corrected.text
    assert followup(corrected.json())["status"] == "correction_requested"
    assert len(corrected.json()["work_items"]) == 2


def test_additional_plants_need_review_and_do_not_automatically_authorize_removal(setup):
    client, _, management, _, team, _, ecology, _ = setup
    report = accept(client, ecology, approved(setup))
    result = findings(setup, report, two=True, other_invasive="yes",
                      finding_latitude=3.1807, finding_longitude=101.5092)
    assert result.status_code == 200, result.text
    awaiting = result.json()
    assert len(awaiting["work_items"]) == 2
    assert followup(awaiting)["status"] == "awaiting_verification"
    assert verify(client, management, awaiting).status_code == 422
    plan = assignment(team, awaiting["revision"], work_type="restoration")
    corrective = verify(client, management, awaiting, next_plan=plan)
    assert corrective.status_code == 200, corrective.text
    assert len(corrective.json()["work_items"]) == 3
    assert corrective.json()["work_items"][-1]["work_type"] == "restoration"


def test_repeat_inspection_keeps_original_restoration_context(setup):
    client, _, management, _, team, _, ecology, _ = setup
    report = accept(client, ecology, approved(setup))
    report = findings(setup, report, regrowth='unknown').json()
    original = followup(report)
    plan = assignment(team, report['revision'], work_type='inspection')
    response = verify(client, management, report, next_plan=plan)
    assert response.status_code == 200, response.text
    repeated = response.json()['work_items'][-1]
    assert repeated['followup_of'] == original['followup_of']
    assert repeated['restoration_snapshot'] == original['restoration_snapshot']


def test_followup_cannot_be_converted_to_removal_by_revising_instructions(setup):
    client, _, management, _, team, _, _, _ = setup
    report=approved(setup);work=followup(report)
    plan=assignment(team,work['revision'],work_type='restoration')
    response=client.post(f"/reports/{report['id']}/work/{work['id']}/revise",headers=management,json=plan)
    assert response.status_code == 422
