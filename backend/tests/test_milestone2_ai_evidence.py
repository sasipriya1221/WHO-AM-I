import os

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.ai.providers import LocalProvider
from app.main import app
from app.models.entities import (
    DNAExperience,
    EvidenceType,
    ExperienceType,
    InputMode,
    MirrorInterest,
    Pattern,
    PatternStatus,
    User,
)
from app.services.dna.engine import extract_evidence, recompute_patterns
from app.services.evidence.guard import assert_dna_eligible
from app.services.evidence.semantic import support_and_counter_evidence


os.environ["WHOAMI_AI_PROVIDER"] = "local"


def _user(db, email="milestone2@example.com"):
    user = User(email=email, display_name="Milestone Two", dna_consent=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _experience(db, user, kind, text):
    exp = DNAExperience(
        user_id=user.id,
        experience_type=kind,
        input_mode=InputMode.TEXT,
        raw_response={"reflection": text},
        consent_for_analysis=True,
    )
    db.add(exp)
    db.flush()
    extract_evidence(db, exp, provider=LocalProvider())
    db.commit()
    return exp


def test_mirror_entertainment_is_rejected_from_dna(db):
    user = _user(db)
    interest = MirrorInterest(user_id=user.id, category="game", name="Angry Birds")
    db.add(interest)
    db.commit()

    assert interest.purpose == "entertainment"
    assert interest.dna_allowed is False
    try:
        assert_dna_eligible(interest)
        assert False, "Mirror data must never pass the DNA guard"
    except PermissionError:
        pass

    assert recompute_patterns(db, user.id) == []


def test_one_reflection_can_only_be_emerging_not_repeated(db):
    user = _user(db, "one-reflection@example.com")
    _experience(db, user, ExperienceType.REFLECTION, "Freedom and control over my own choices matter to me.")
    patterns = recompute_patterns(db, user.id)
    autonomy = next(p for p in patterns if p.ai_label == "autonomy")
    assert autonomy.support_count >= 1
    assert autonomy.status == PatternStatus.EMERGING
    assert autonomy.status != PatternStatus.REPEATED


def test_repeated_requires_independent_experiences(db):
    user = _user(db, "independent@example.com")
    _experience(db, user, ExperienceType.EMPTY_ROOM, "I put freedom and choice closest to me.")
    _experience(db, user, ExperienceType.FUTURE_ME, "I want control over my own choices in the future.")
    _experience(db, user, ExperienceType.REFLECTION, "I feel independent when I choose my own direction.")
    patterns = recompute_patterns(db, user.id)
    autonomy = next(p for p in patterns if p.ai_label == "autonomy")
    assert autonomy.status == PatternStatus.REPEATED


def test_semantic_challenge_returns_counter_evidence(db):
    user = _user(db, "counter@example.com")
    _experience(db, user, ExperienceType.EMPTY_ROOM, "Freedom and choice feel important to me.")
    _experience(db, user, ExperienceType.FUTURE_ME, "I want control over my own direction.")
    _experience(db, user, ExperienceType.REFLECTION, "I do not always want complete freedom; too many choices can overwhelm me.")
    recompute_patterns(db, user.id)

    result = support_and_counter_evidence(db, user.id, "autonomy freedom choice", provider=LocalProvider())
    assert result["supporting"]
    assert result["contradicting"]


def test_why_challenge_rename_and_not_me_flows():
    client = TestClient(app)
    user = client.post(
        "/api/v1/users/demo",
        json={"display_name": "Flow User", "email": "milestone2-flow@demo.local"},
    ).json()
    uid = user["id"]
    client.post(f"/api/v1/dna/{uid}/consent", json={"consent": True})

    for kind, text in [
        ("empty_room", "Freedom and choice are close to me."),
        ("future_me", "I want control over my own choices."),
        ("reflection", "I feel independent when I choose my own direction."),
        ("reflection", "I do not always want complete freedom; too many choices overwhelm me."),
    ]:
        response = client.post(
            f"/api/v1/dna/{uid}/experiences",
            json={"experience_type": kind, "input_mode": "text", "response": {"reflection": text}, "consent_for_analysis": True},
        )
        assert response.status_code == 200

    patterns = client.get(f"/api/v1/dna/{uid}/patterns").json()
    autonomy = next(p for p in patterns if p["label"] == "autonomy")
    pid = autonomy["id"]

    why = client.get(f"/api/v1/dna/{uid}/patterns/{pid}/why")
    assert why.status_code == 200
    assert why.json()["supporting"]

    challenge = client.post(f"/api/v1/dna/{uid}/patterns/{pid}/challenge")
    assert challenge.status_code == 200
    assert challenge.json()["contradicting"]
    assert challenge.json()["status"] == "questioned"

    strands = client.get(f"/api/v1/dna/{uid}/strands").json()
    strand = next(s for s in strands if s["pattern_id"] == pid)
    rename = client.post(
        f"/api/v1/dna/{uid}/strands/{strand['id']}/rename",
        json={"user_label": "Having control over my own choices"},
    )
    assert rename.status_code == 200
    assert rename.json()["status"] == "user_defined"
    assert rename.json()["ai_label"] == "autonomy"

    reject = client.post(f"/api/v1/dna/{uid}/patterns/{pid}/not-me")
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"
