from __future__ import annotations

import json
from dataclasses import dataclass, fields
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.entities import (
    DNAExperience,
    DNAStrand,
    Evidence,
    Pattern,
    PatternEvidence,
)


@dataclass(frozen=True)
class DatabaseInferenceSnapshot:
    """User-scoped persistence state before or after an inference attempt."""

    experiences: tuple[tuple[Any, ...], ...]
    evidence: tuple[tuple[Any, ...], ...]
    graph_edges: tuple[tuple[Any, ...], ...]
    patterns: tuple[tuple[Any, ...], ...]
    dna_strands: tuple[tuple[Any, ...], ...]
    # TODO(repository-specific): There is no persisted embedding model/table yet.
    # Evidence.embedding_ref plus provider embed-call snapshots are the concrete
    # repository-backed signals. Extend this field when an embedding store lands.
    embedding_refs: tuple[tuple[str, str], ...]


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _stable_rows(rows: list[tuple[Any, ...]]) -> tuple[tuple[Any, ...], ...]:
    return tuple(sorted(rows, key=repr))


def database_inference_snapshot(db: Session, user_id: str) -> DatabaseInferenceSnapshot:
    """Capture every stored artifact that can affect a user's DNA inference."""

    db.expire_all()
    experiences = db.scalars(
        select(DNAExperience).where(DNAExperience.user_id == user_id)
    ).all()
    evidence_items = db.scalars(
        select(Evidence).where(Evidence.user_id == user_id)
    ).all()
    patterns = db.scalars(
        select(Pattern).where(Pattern.user_id == user_id)
    ).all()
    strands = db.scalars(
        select(DNAStrand).where(DNAStrand.user_id == user_id)
    ).all()
    edges = db.scalars(
        select(PatternEvidence)
        .join(Pattern, Pattern.id == PatternEvidence.pattern_id)
        .where(Pattern.user_id == user_id)
    ).all()

    return DatabaseInferenceSnapshot(
        experiences=_stable_rows(
            [
                (
                    item.id,
                    _enum_value(item.experience_type),
                    _enum_value(item.input_mode),
                    json.dumps(item.raw_response, sort_keys=True),
                    item.purpose,
                    item.consent_for_analysis,
                )
                for item in experiences
            ]
        ),
        evidence=_stable_rows(
            [
                (
                    item.id,
                    item.experience_id,
                    item.source_type,
                    json.dumps(item.source_reference, sort_keys=True),
                    item.purpose,
                    item.candidate_concept,
                    _enum_value(item.evidence_type),
                    item.normalized_summary,
                    item.original_text,
                    _enum_value(item.strength),
                    item.embedding_ref,
                )
                for item in evidence_items
            ]
        ),
        graph_edges=_stable_rows(
            [
                (item.id, item.pattern_id, item.evidence_id, _enum_value(item.relationship))
                for item in edges
            ]
        ),
        patterns=_stable_rows(
            [
                (
                    item.id,
                    item.ai_label,
                    item.description,
                    _enum_value(item.status),
                    item.support_count,
                    item.contradiction_count,
                    item.source,
                )
                for item in patterns
            ]
        ),
        dna_strands=_stable_rows(
            [
                (
                    item.id,
                    item.pattern_id,
                    item.ai_original_label,
                    item.user_label,
                    _enum_value(item.status),
                )
                for item in strands
            ]
        ),
        embedding_refs=_stable_rows(
            [
                (item.id, item.embedding_ref)
                for item in evidence_items
                if item.embedding_ref is not None
            ]
        ),
    )


def app_database_inference_snapshot(user_id: str) -> DatabaseInferenceSnapshot:
    """Capture app-database state without holding a read transaction over an API call."""

    with SessionLocal() as db:
        return database_inference_snapshot(db, user_id)


def assert_no_inference_side_effects(
    before: DatabaseInferenceSnapshot,
    after: DatabaseInferenceSnapshot,
) -> None:
    changes = []
    for field in fields(DatabaseInferenceSnapshot):
        old = getattr(before, field.name)
        new = getattr(after, field.name)
        if old != new:
            changes.append(f"{field.name}: before={old!r}; after={new!r}")
    assert not changes, "Blocked input changed inference state:\n" + "\n".join(changes)


def public_inference_snapshot(client: TestClient, user_id: str) -> dict[str, Any]:
    response = client.get(f"/api/v1/vault/{user_id}/inference-map")
    assert response.status_code == 200
    return response.json()


def create_demo_user(
    client: TestClient,
    *,
    email: str,
    consent: bool = False,
) -> str:
    response = client.post(
        "/api/v1/users/demo",
        json={"display_name": "Security Regression", "email": email},
    )
    assert response.status_code == 200
    user_id = response.json()["id"]
    if consent:
        consent_response = client.post(
            f"/api/v1/dna/{user_id}/consent",
            json={"consent": True},
        )
        assert consent_response.status_code == 200
    return user_id


def experience_request(text: str, *, consent_for_analysis: bool = True) -> dict[str, Any]:
    return {
        "experience_type": "reflection",
        "input_mode": "text",
        "response": {"reflection": text},
        "consent_for_analysis": consent_for_analysis,
    }
