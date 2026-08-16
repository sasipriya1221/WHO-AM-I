import pytest

from tests.provider_spies import NO_PROVIDER_CALLS
from tests.security_helpers import (
    app_database_inference_snapshot,
    assert_no_inference_side_effects,
    create_demo_user,
    experience_request,
    public_inference_snapshot,
)


pytestmark = pytest.mark.security

HIGH_RISK_TEXT = "Sometimes I think about how to hurt myself when things get bad."
SAFE_TEXT = "Having control over my own choices feels important to me."


def _post_reflection(client, user_id: str, text: str):
    return client.post(
        f"/api/v1/dna/{user_id}/experiences",
        json=experience_request(text),
    )


def _assert_direct_ingestion_block(response) -> None:
    assert response.status_code == 403
    body = response.json()
    # TODO(repository-specific): The direct ingestion route has no existing
    # safety-block error envelope. Keep the current FastAPI {"detail": ...}
    # convention, then lock this to an exact message when that API is defined.
    assert set(body) == {"detail"}
    assert isinstance(body["detail"], str)
    detail = body["detail"].lower()
    assert "high-risk" in detail or "safety" in detail
    assert "dna" in detail or "evidence" in detail


def test_safety_check_flags_high_risk_reflection(client):
    response = client.post("/api/v1/safety/check", json={"text": HIGH_RISK_TEXT})

    assert response.status_code == 200
    assert response.json() == {
        "allow_dna_processing": False,
        "risk": "high",
        "note": "High-risk content must not become Happiness DNA evidence.",
    }


def test_direct_dna_ingestion_cannot_bypass_safety_check(client, provider_spy):
    user_id = create_demo_user(
        client,
        email="safety-direct-bypass@demo.local",
        consent=True,
    )

    # Deliberately do not call /api/v1/safety/check first. The evidence-producing
    # endpoint must enforce the boundary authoritatively on its own.
    response = _post_reflection(client, user_id, HIGH_RISK_TEXT)

    _assert_direct_ingestion_block(response)
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS


def test_blocked_high_risk_reflection_has_zero_downstream_side_effects(
    client,
    provider_spy,
):
    user_id = create_demo_user(
        client,
        email="safety-zero-side-effects@demo.local",
        consent=True,
    )
    before_db = app_database_inference_snapshot(user_id)
    before_public = public_inference_snapshot(client, user_id)

    _post_reflection(client, user_id, HIGH_RISK_TEXT)

    after_db = app_database_inference_snapshot(user_id)
    after_public = public_inference_snapshot(client, user_id)
    assert_no_inference_side_effects(before_db, after_db)
    assert after_public == before_public
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS


def test_safe_reflection_positive_control_creates_inference(client, provider_spy):
    user_id = create_demo_user(
        client,
        email="safety-positive-control@demo.local",
        consent=True,
    )
    before = app_database_inference_snapshot(user_id)

    response = _post_reflection(client, user_id, SAFE_TEXT)

    assert response.status_code == 200
    assert response.json()["evidence_created"] == 1
    after = app_database_inference_snapshot(user_id)
    assert len(after.experiences) == len(before.experiences) + 1
    assert len(after.evidence) == len(before.evidence) + 1
    assert len(after.graph_edges) == len(before.graph_edges) + 1
    assert len(after.patterns) == len(before.patterns) + 1
    assert len(after.dna_strands) == len(before.dna_strands) + 1
    assert after.embedding_refs == ()
    assert provider_spy.extract_calls == [(f"reflection {SAFE_TEXT}", "reflection")]

    public = public_inference_snapshot(client, user_id)
    assert len(public["self_discovery"]) == 1
    assert len(public["dna"]) == 1
