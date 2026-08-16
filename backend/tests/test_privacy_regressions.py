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
SAFE_TEXT = "I feel independent when I choose my own direction."


def _post_reflection(
    client,
    user_id: str,
    text: str,
    *,
    consent_for_analysis: bool = True,
):
    return client.post(
        f"/api/v1/dna/{user_id}/experiences",
        json=experience_request(
            text,
            consent_for_analysis=consent_for_analysis,
        ),
    )


def test_high_risk_text_is_not_retained_in_database_or_vault(client, provider_spy):
    user_id = create_demo_user(
        client,
        email="privacy-high-risk-retention@demo.local",
        consent=True,
    )
    before = app_database_inference_snapshot(user_id)

    response = _post_reflection(client, user_id, HIGH_RISK_TEXT)

    assert response.status_code == 403
    after = app_database_inference_snapshot(user_id)
    assert_no_inference_side_effects(before, after)
    assert HIGH_RISK_TEXT not in repr(after)
    assert HIGH_RISK_TEXT not in repr(public_inference_snapshot(client, user_id))
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS


def test_missing_dna_consent_blocks_before_storage_or_provider(client, provider_spy):
    user_id = create_demo_user(
        client,
        email="privacy-no-dna-consent@demo.local",
    )
    before_db = app_database_inference_snapshot(user_id)
    before_public = public_inference_snapshot(client, user_id)

    response = _post_reflection(client, user_id, SAFE_TEXT)

    assert response.status_code == 403
    assert response.json() == {"detail": "DNA consent required"}
    after_db = app_database_inference_snapshot(user_id)
    assert_no_inference_side_effects(before_db, after_db)
    assert public_inference_snapshot(client, user_id) == before_public
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS


def test_analysis_consent_false_is_off_the_record(client, provider_spy):
    user_id = create_demo_user(
        client,
        email="privacy-off-record@demo.local",
        consent=True,
    )
    before_db = app_database_inference_snapshot(user_id)
    before_public = public_inference_snapshot(client, user_id)

    response = _post_reflection(
        client,
        user_id,
        SAFE_TEXT,
        consent_for_analysis=False,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Use off-the-record mode for non-analysed experiences"
    }
    after_db = app_database_inference_snapshot(user_id)
    assert_no_inference_side_effects(before_db, after_db)
    assert public_inference_snapshot(client, user_id) == before_public
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS


def test_entertainment_data_stays_out_of_self_discovery_and_dna(client, provider_spy):
    user_id = create_demo_user(
        client,
        email="privacy-entertainment@demo.local",
    )

    response = client.post(
        f"/api/v1/mirror/{user_id}/interests",
        json={"category": "series", "name": "Game of Thrones"},
    )

    assert response.status_code == 200
    assert response.json()["dna_allowed"] is False
    inference = public_inference_snapshot(client, user_id)
    assert inference["entertainment"] == [
        {
            "id": response.json()["id"],
            "label": "Game of Thrones",
            "purpose": "entertainment",
            "dna_allowed": False,
        }
    ]
    assert inference["self_discovery"] == []
    assert inference["dna"] == []
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS
