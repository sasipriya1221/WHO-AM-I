from __future__ import annotations

import math
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import AIProvider, get_ai_provider
from app.models.entities import Evidence, EvidenceType


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    denom = math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b))
    if not denom:
        return 0.0
    return sum(x*y for x, y in zip(a, b)) / denom


def retrieve_related(
    db: Session,
    user_id: str,
    query: str,
    *,
    evidence_type: EvidenceType | None = None,
    limit: int = 5,
    provider: AIProvider | None = None,
) -> list[tuple[Evidence, float]]:
    provider = provider or get_ai_provider()
    items = db.scalars(select(Evidence).where(Evidence.user_id == user_id)).all()
    if evidence_type is not None:
        items = [e for e in items if e.evidence_type == evidence_type]
    if not items:
        return []
    texts = [f"{e.candidate_concept}. {e.normalized_summary}. {e.original_text or ''}" for e in items]
    vectors = provider.embed([query] + texts)
    qv = vectors[0]
    scored = [(e, cosine(qv, v)) for e, v in zip(items, vectors[1:])]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def support_and_counter_evidence(
    db: Session,
    user_id: str,
    query: str,
    *,
    limit: int = 5,
    provider: AIProvider | None = None,
) -> dict[str, list[dict]]:
    provider = provider or get_ai_provider()
    support = retrieve_related(db, user_id, query, evidence_type=EvidenceType.SUPPORT, limit=limit, provider=provider)
    counter = retrieve_related(db, user_id, query, evidence_type=EvidenceType.CONTRADICT, limit=limit, provider=provider)
    def serialize(rows):
        return [
            {
                "id": e.id,
                "concept": e.candidate_concept,
                "summary": e.normalized_summary,
                "original": e.original_text,
                "experience_id": e.experience_id,
                "similarity": round(score, 4),
            }
            for e, score in rows
        ]
    return {"supporting": serialize(support), "contradicting": serialize(counter)}
