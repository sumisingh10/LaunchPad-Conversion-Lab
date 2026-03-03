"""Integration tests for the campaign optimization API flow.
Covers auth, campaign creation, variant generation, simulation, recommendations, apply/save, and baseline lifecycle endpoints.
"""
from datetime import datetime, timedelta, timezone
import time

from sqlalchemy import select

from app.models.campaign import Campaign
from app.models.lift_trace_event import LiftTraceEvent


def signup_and_auth(client):
    """Register and return and auth."""
    r = client.post("/auth/signup", json={"email": "u@test.com", "password": "pass1234", "name": "U"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_generate_variants_endpoint(client, monkeypatch):
    """Verify generate variants endpoint."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "C1",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    res = client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 3

    second = client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    assert second.status_code == 200
    assert len(second.json()) == 3


def test_propose_and_apply_recommendation(client):
    """Verify propose and apply recommendation."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "C1",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {"required_trust_phrase": "warranty"},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/simulate-batch", headers=headers)

    propose = client.post(f"/campaigns/{campaign['id']}/propose-improvements", headers=headers)
    assert propose.status_code == 200
    recommendations = client.get(f"/campaigns/{campaign['id']}/recommendations", headers=headers).json()
    assert len(recommendations) >= 1
    assert "adjusted_priority_score" in recommendations[0]["expected_impact_json"]

    rid = recommendations[0]["id"]
    approve = client.post(f"/recommendations/{rid}/approve", headers=headers)
    assert approve.status_code == 200

    apply = client.post(f"/recommendations/{rid}/apply", headers=headers)
    assert apply.status_code == 200
    assert apply.json()["status"] == "APPLIED"

    trace = client.get(f"/campaigns/{campaign['id']}/lift-trace", headers=headers)
    assert trace.status_code == 200
    assert len(trace.json()) >= 1


def test_trust_focus_returns_three_recommendations_when_phrase_required(client):
    """Verify trust-callout focus yields three guardrail-compliant options."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Trust Focus Campaign",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {"required_trust_phrase": "free returns"},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    baseline_id = variants[0]["id"]

    propose = client.post(
        f"/campaigns/{campaign['id']}/propose-improvements",
        headers=headers,
        json={"focus_component": "hero.trust_callout", "selected_variant_id": baseline_id},
    )
    assert propose.status_code == 200
    body = propose.json()
    assert len(body) == 3
    for rec in body:
        op = rec["patch_json"]["operations"][0]
        assert op["path"] == "hero.trust_callout"
        assert "free returns" in str(op["value"]).lower()


def test_guardrail_blocks_overly_large_patch(client, monkeypatch):
    """Verify guardrail blocks overly large patch."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "C2",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {"max_char_delta_per_change": 20},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/simulate-batch", headers=headers)

    from app.schemas.recommendation import CodexRecommendationResponse
    from app.services.codex_service import CodexService

    def mocked_propose(self, inputs):
        """Provide mocked behavior for propose."""
        _ = inputs
        return CodexRecommendationResponse.model_validate(
            {
                "recommendations": [
                    {
                        "rank": 1,
                        "change_type": "COPY",
                        "target_component": "hero.headline",
                        "rationale": "Large rewrite",
                        "hypothesis": "Might improve CTR",
                        "expected_impact_json": {"ctr": "up"},
                        "patch": {
                            "operations": [
                                {
                                    "op": "replace",
                                    "path": "hero.headline",
                                    "value": "X" * 180,
                                    "reason": "Rewrite entire hero",
                                }
                            ]
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr(CodexService, "propose_improvements", mocked_propose)

    propose = client.post(f"/campaigns/{campaign['id']}/propose-improvements", headers=headers)
    assert propose.status_code == 200
    assert propose.json() == []

    recommendations = client.get(f"/campaigns/{campaign['id']}/recommendations", headers=headers).json()
    assert recommendations == []

    trace = client.get(f"/campaigns/{campaign['id']}/lift-trace", headers=headers).json()
    assert any("Guardrail blocked recommendation" in event["summary"] for event in trace)


def test_recommendation_feedback_roundtrip(client):
    """Verify recommendation feedback roundtrip."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Feedback Campaign",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/simulate-batch", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/propose-improvements", headers=headers)

    recommendations = client.get(f"/campaigns/{campaign['id']}/recommendations", headers=headers).json()
    assert len(recommendations) >= 1
    rid = recommendations[0]["id"]

    feedback = client.post(
        f"/recommendations/{rid}/feedback",
        headers=headers,
        json={"sentiment": "POSITIVE", "rating": 5, "comment": "Useful and clear"},
    )
    assert feedback.status_code == 200

    summary = client.get(f"/campaigns/{campaign['id']}/feedback-summary", headers=headers)
    assert summary.status_code == 200
    row = [item for item in summary.json() if item["recommendation_id"] == rid][0]
    assert row["positive_count"] >= 1


def test_set_and_revert_baseline_variant(client):
    """Verify set and revert baseline variant."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Baseline Campaign",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    assert len(variants) >= 1
    original_id = variants[0]["id"]

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    target_id = variants[-1]["id"]

    set_baseline = client.post(
        f"/campaigns/{campaign['id']}/baseline",
        headers=headers,
        json={"variant_id": target_id, "baseline_name": "Spring Baseline V2"},
    )
    assert set_baseline.status_code == 200
    assert set_baseline.json()["constraints_json"]["baseline_variant_id"] == target_id
    assert set_baseline.json()["constraints_json"]["original_baseline_variant_id"] == original_id
    updated_variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    renamed = [item for item in updated_variants if item["id"] == target_id][0]
    assert renamed["name"] == "Spring Baseline V2"

    revert = client.post(f"/campaigns/{campaign['id']}/baseline/revert", headers=headers)
    assert revert.status_code == 200
    assert revert.json()["constraints_json"]["baseline_variant_id"] == original_id


def test_delete_campaign(client):
    """Verify campaign deletion still succeeds when variant version chains exist."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Delete Me",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    assert variants
    variant_id = variants[0]["id"]
    manual_edit = client.post(
        f"/variants/{variant_id}/manual-edit",
        headers=headers,
        json={"path": "hero.headline", "value": "Delete Me Updated", "reason": "create version chain"},
    )
    assert manual_edit.status_code == 200

    deleted = client.delete(f"/campaigns/{campaign['id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True

    missing = client.get(f"/campaigns/{campaign['id']}", headers=headers)
    assert missing.status_code == 404


def test_delete_variant_removes_associated_kpi_and_recommendation_data(client):
    """Ensure deleting a non-baseline variant removes it from variants, metrics, and recommendation lists."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Delete Variant",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/simulate-batch", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/propose-improvements", headers=headers)

    campaign_detail = client.get(f"/campaigns/{campaign['id']}", headers=headers).json()
    baseline_id = campaign_detail["constraints_json"]["baseline_variant_id"]
    variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    target_variant = next(item for item in variants if item["id"] != baseline_id)

    metrics_before = client.get(f"/campaigns/{campaign['id']}/metrics", headers=headers).json()
    assert any(row["variant_id"] == target_variant["id"] for row in metrics_before)

    deleted = client.delete(f"/variants/{target_variant['id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True

    variants_after = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    assert all(item["id"] != target_variant["id"] for item in variants_after)

    metrics_after = client.get(f"/campaigns/{campaign['id']}/metrics", headers=headers).json()
    assert all(row["variant_id"] != target_variant["id"] for row in metrics_after)

    recommendations_after = client.get(f"/campaigns/{campaign['id']}/recommendations", headers=headers).json()
    assert all(item["variant_id"] != target_variant["id"] for item in recommendations_after)


def test_delete_variant_rejects_baseline_variant(client):
    """Reject deletion attempts for the active baseline variant."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Delete Baseline Guard",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    campaign_detail = client.get(f"/campaigns/{campaign['id']}", headers=headers).json()
    baseline_id = campaign_detail["constraints_json"]["baseline_variant_id"]

    blocked = client.delete(f"/variants/{baseline_id}", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "Baseline variant cannot be deleted"


def test_campaign_get_repairs_missing_baseline_constraints(client, db_session):
    """Backfill missing baseline ids on campaign read for legacy rows."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Legacy Baseline Repair",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    baseline_id = variants[0]["id"]

    campaign_row = db_session.scalar(select(Campaign).where(Campaign.id == campaign["id"]))
    campaign_row.constraints_json = {}
    db_session.commit()

    repaired = client.get(f"/campaigns/{campaign['id']}", headers=headers)
    assert repaired.status_code == 200
    assert repaired.json()["constraints_json"]["baseline_variant_id"] == baseline_id
    assert repaired.json()["constraints_json"]["original_baseline_variant_id"] == baseline_id


def test_save_variant_rejects_duplicate_name(client):
    """Reject save-variant requests when a user-provided name already exists in the campaign."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Duplicate Guard",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    assert variants
    duplicate_name = variants[0]["name"]

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/simulate-batch", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/propose-improvements", headers=headers)
    recommendations = client.get(f"/campaigns/{campaign['id']}/recommendations", headers=headers).json()
    assert recommendations

    response = client.post(
        f"/recommendations/{recommendations[0]['id']}/save-variant",
        headers=headers,
        json={"variant_name": duplicate_name},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Variant name already exists"


def test_save_variant_rejects_reserved_baseline_name(client):
    """Reject save-variant requests that try to use the reserved baseline variant name."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Reserved Name Guard",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/simulate-batch", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/propose-improvements", headers=headers)
    recommendations = client.get(f"/campaigns/{campaign['id']}/recommendations", headers=headers).json()
    assert recommendations

    response = client.post(
        f"/recommendations/{recommendations[0]['id']}/save-variant",
        headers=headers,
        json={"variant_name": "Baseline"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Baseline is reserved for the active baseline variant"


def test_admin_approval_status_transitions(client, db_session):
    """Validate submit/re-submit/auto-approved status behavior for simulated admin approvals."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Admin Flow",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/simulate-batch", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/propose-improvements", headers=headers)
    recommendation = client.get(f"/campaigns/{campaign['id']}/recommendations", headers=headers).json()[0]
    saved_variant = client.post(
        f"/recommendations/{recommendation['id']}/save-variant",
        headers=headers,
        json={"variant_name": "Approval Variant"},
    ).json()

    submit = client.post(f"/variants/{saved_variant['id']}/submit-admin-approval", headers=headers)
    assert submit.status_code == 200
    assert submit.json()["status"] == "PENDING_ADMIN_APPROVAL"

    immediate_resubmit = client.post(f"/variants/{saved_variant['id']}/submit-admin-approval", headers=headers)
    assert immediate_resubmit.status_code == 200
    assert immediate_resubmit.json()["message"] == "Already sent for approval. Please wait a few seconds."

    status_pending = client.get(f"/variants/{saved_variant['id']}/admin-approval-status", headers=headers)
    assert status_pending.status_code == 200
    assert status_pending.json()["status"] == "PENDING_ADMIN_APPROVAL"

    submitted_event = next(
        (
            event
            for event in db_session.scalars(
                select(LiftTraceEvent)
                .where(LiftTraceEvent.variant_id == saved_variant["id"])
                .order_by(LiftTraceEvent.created_at.desc())
            ).all()
            if isinstance(event.metadata_json, dict) and event.metadata_json.get("workflow_stage") == "ADMIN_APPROVAL_SUBMITTED"
        ),
        None,
    )
    assert submitted_event is not None
    submitted_event.created_at = datetime.now(timezone.utc) - timedelta(seconds=12)
    db_session.commit()

    status_approved = client.get(f"/variants/{saved_variant['id']}/admin-approval-status", headers=headers)
    assert status_approved.status_code == 200
    assert status_approved.json()["status"] == "APPROVED"


def test_advise_job_endpoint_returns_result(client):
    """Run async advise job endpoint and verify a final success status with result payload."""
    headers = signup_and_auth(client)
    campaign = client.post(
        "/campaigns",
        headers=headers,
        json={
            "name": "Async Advice",
            "product_title": "Bag",
            "product_category": "Bags",
            "product_description": "Desc",
            "objective": "CTR",
            "audience_segment": "Segment",
            "constraints_json": {},
            "primary_kpi": "CTR",
            "status": "RUNNING",
        },
    ).json()

    client.post(f"/campaigns/{campaign['id']}/generate-variants", headers=headers)
    client.post(f"/campaigns/{campaign['id']}/simulate-batch", headers=headers)
    variants = client.get(f"/campaigns/{campaign['id']}/variants", headers=headers).json()
    variant_ids = [item["id"] for item in variants]

    started = client.post(
        f"/campaigns/{campaign['id']}/advise-variants/jobs",
        headers=headers,
        json={"user_goal": "maximize ctr", "variant_ids": variant_ids},
    )
    assert started.status_code == 200
    job_id = started.json()["job_id"]

    final = None
    for _ in range(60):
        status_response = client.get(f"/campaigns/{campaign['id']}/advise-variants/jobs/{job_id}", headers=headers)
        assert status_response.status_code == 200
        payload = status_response.json()
        if payload["status"] in {"SUCCEEDED", "FAILED"}:
            final = payload
            break
        time.sleep(0.1)

    assert final is not None
    assert final["status"] == "SUCCEEDED"
    assert isinstance(final.get("result"), dict)
    assert "best_variant_id" in final["result"]
