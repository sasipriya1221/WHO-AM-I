from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.core.purpose import DataPurpose
from app.models.entities import (
    DNAExperience,
    ExperienceType,
    InputMode,
    MirrorInterest,
    User,
)
from app.services.dna.engine import extract_evidence, recompute_patterns
from app.services.evidence.guard import assert_dna_eligible
from tests.provider_spies import NO_PROVIDER_CALLS
from tests.security_helpers import (
    app_database_inference_snapshot,
    assert_no_inference_side_effects,
    create_demo_user,
    database_inference_snapshot,
    public_inference_snapshot,
)


pytestmark = pytest.mark.security


def _db_user(db: Session, email: str) -> User:
    user = User(email=email, display_name="DNA Eligibility", dna_consent=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_dna_allowed_false_is_an_authoritative_guard_condition():
    # assert_dna_eligible accepts a record-shaped object rather than a concrete
    # model. This boundary double isolates dna_allowed from Mirror class-name and
    # purpose checks, proving the boolean is itself a veto.
    record = SimpleNamespace(
        purpose=DataPurpose.SELF_DISCOVERY.value,
        consent_for_analysis=True,
        dna_allowed=False,
    )

    with pytest.raises(PermissionError, match="dna_allowed"):
        assert_dna_eligible(record)


def test_dna_allowed_true_positive_control_passes_the_generic_guard():
    record = SimpleNamespace(
        purpose=DataPurpose.SELF_DISCOVERY.value,
        consent_for_analysis=True,
        dna_allowed=True,
    )

    assert_dna_eligible(record)


def test_dna_allowed_false_is_rejected_before_provider_or_inference(db, provider_spy):
    # TODO(repository-specific): No HTTP route currently accepts a stored
    # MirrorInterest for DNA ingestion. extract_evidence is the real service
    # boundary and should remain covered if such a route is introduced.
    user = _db_user(db, "dna-allowed-false@example.com")
    interest = MirrorInterest(
        user_id=user.id,
        category="game",
        name="Angry Birds",
        purpose=DataPurpose.ENTERTAINMENT.value,
        dna_allowed=False,
    )
    db.add(interest)
    db.commit()
    before = database_inference_snapshot(db, user.id)

    with pytest.raises(PermissionError):
        extract_evidence(db, interest, provider=provider_spy)

    after = database_inference_snapshot(db, user.id)
    assert_no_inference_side_effects(before, after)
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS


def test_dna_allowed_false_remains_blocked_if_purpose_is_misclassified(db, provider_spy):
    user = _db_user(db, "dna-allowed-tampered-purpose@example.com")
    interest = MirrorInterest(
        user_id=user.id,
        category="series",
        name="Game of Thrones",
        # This deliberately simulates a bad import/migration. dna_allowed=False
        # must remain a defense-in-depth veto even if purpose is misclassified.
        purpose=DataPurpose.SELF_DISCOVERY.value,
        dna_allowed=False,
    )
    db.add(interest)
    db.commit()
    before = database_inference_snapshot(db, user.id)

    with pytest.raises(PermissionError):
        assert_dna_eligible(interest)
    with pytest.raises(PermissionError):
        extract_evidence(db, interest, provider=provider_spy)

    after = database_inference_snapshot(db, user.id)
    assert_no_inference_side_effects(before, after)
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS


def test_consented_self_discovery_experience_positive_control_is_eligible(
    db,
    provider_spy,
):
    user = _db_user(db, "dna-eligible-positive@example.com")
    experience = DNAExperience(
        user_id=user.id,
        experience_type=ExperienceType.REFLECTION,
        input_mode=InputMode.TEXT,
        raw_response={"reflection": "Having control over my choices matters."},
        purpose=DataPurpose.SELF_DISCOVERY.value,
        consent_for_analysis=True,
    )
    db.add(experience)
    db.commit()
    before = database_inference_snapshot(db, user.id)

    assert_dna_eligible(experience)
    created = extract_evidence(db, experience, provider=provider_spy)
    db.commit()
    recompute_patterns(db, user.id)

    assert len(created) == 1
    after = database_inference_snapshot(db, user.id)
    assert len(after.experiences) == len(before.experiences)
    assert len(after.evidence) == len(before.evidence) + 1
    assert len(after.graph_edges) == len(before.graph_edges) + 1
    assert len(after.patterns) == len(before.patterns) + 1
    assert len(after.dna_strands) == len(before.dna_strands) + 1
    assert provider_spy.extract_calls == [
        ("reflection Having control over my choices matters.", "reflection")
    ]


def test_mirror_api_persists_dna_allowed_false_without_inference(
    client,
    provider_spy,
):
    user_id = create_demo_user(
        client,
        email="dna-allowed-api@demo.local",
    )

    response = client.post(
        f"/api/v1/mirror/{user_id}/interests",
        json={"category": "game", "name": "Angry Birds"},
    )

    assert response.status_code == 200
    assert response.json()["purpose"] == "entertainment"
    assert response.json()["dna_allowed"] is False
    stored = app_database_inference_snapshot(user_id)
    assert stored.experiences == ()
    assert stored.evidence == ()
    assert stored.embedding_refs == ()
    assert stored.graph_edges == ()
    assert stored.patterns == ()
    assert stored.dna_strands == ()
    public = public_inference_snapshot(client, user_id)
    assert public["entertainment"][0]["dna_allowed"] is False
    assert public["self_discovery"] == []
    assert public["dna"] == []
    assert provider_spy.snapshot() == NO_PROVIDER_CALLS
