from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import DNAStrand, Evidence, MirrorInterest, Pattern, PatternEvidence
from app.services.dna.engine import recompute_patterns

# This router is included inside the existing /api/v1 router.
vault_router = APIRouter()


def _strand_for_pattern(db: Session, user_id: str, pattern_id: str):
    return db.scalar(
        select(DNAStrand).where(
            DNAStrand.user_id == user_id,
            DNAStrand.pattern_id == pattern_id,
        )
    )


def _pattern_snapshot(db: Session, user_id: str, pattern_id: str):
    pattern = db.get(Pattern, pattern_id)
    if not pattern or pattern.user_id != user_id:
        return None
    strand = _strand_for_pattern(db, user_id, pattern.id)
    return {
        "pattern_id": pattern.id,
        "ai_label": pattern.ai_label,
        "pattern_status": pattern.status.value,
        "support_count": pattern.support_count,
        "contradiction_count": pattern.contradiction_count,
        "strand_id": strand.id if strand else None,
        "strand_status": strand.status.value if strand else None,
        "user_label": strand.user_label if strand else None,
        "display_label": (strand.user_label if strand and strand.user_label else pattern.ai_label),
        "ownership_state": "user_defined" if strand and strand.user_label else "ai_hypothesis",
    }


def _change_message(before: dict, after: dict):
    if before["pattern_status"] != after["pattern_status"]:
        return (
            f"Evidence changed this pattern from {before['pattern_status']} "
            f"to {after['pattern_status']}."
        )
    if before["support_count"] != after["support_count"]:
        return (
            f"The label stayed {after['pattern_status']}, but supporting evidence "
            f"fell from {before['support_count']} to {after['support_count']}."
        )
    return "This deletion did not change the current pattern state."


@vault_router.get("/vault/{user_id}/inference-map")
def inference_map(user_id: str, db: Session = Depends(get_db)):
    interests = db.scalars(
        select(MirrorInterest).where(MirrorInterest.user_id == user_id)
    ).all()
    evidence_items = db.scalars(
        select(Evidence).where(Evidence.user_id == user_id)
    ).all()
    patterns = db.scalars(
        select(Pattern).where(Pattern.user_id == user_id)
    ).all()

    evidence_payload = []
    for evidence in evidence_items:
        links = db.scalars(
            select(PatternEvidence).where(PatternEvidence.evidence_id == evidence.id)
        ).all()
        affects = []
        for link in links:
            snap = _pattern_snapshot(db, user_id, link.pattern_id)
            if snap:
                affects.append({**snap, "relationship": link.relationship.value})
        evidence_payload.append(
            {
                "id": evidence.id,
                "concept": evidence.candidate_concept,
                "summary": evidence.normalized_summary,
                "original": evidence.original_text,
                "experience_id": evidence.experience_id,
                "experience_type": (evidence.source_reference or {}).get("experience_type"),
                "evidence_type": evidence.evidence_type.value,
                "affects": affects,
            }
        )

    dna_payload = []
    for pattern in patterns:
        snap = _pattern_snapshot(db, user_id, pattern.id)
        if snap:
            dna_payload.append(snap)

    return {
        "entertainment": [
            {
                "id": item.id,
                "label": item.name,
                "purpose": item.purpose,
                "dna_allowed": item.dna_allowed,
            }
            for item in interests
        ],
        "self_discovery": evidence_payload,
        "dna": dna_payload,
        "principle": "If you remove part of your story, AI loses the right to use that evidence.",
    }


@vault_router.get("/vault/{user_id}/evidence/{evidence_id}/impact")
def preview_evidence_impact(user_id: str, evidence_id: str, db: Session = Depends(get_db)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence or evidence.user_id != user_id:
        raise HTTPException(404, "Evidence not found")
    links = db.scalars(
        select(PatternEvidence).where(PatternEvidence.evidence_id == evidence.id)
    ).all()
    affected = []
    for link in links:
        snap = _pattern_snapshot(db, user_id, link.pattern_id)
        if snap:
            affected.append({**snap, "relationship": link.relationship.value})
    return {
        "evidence": {
            "id": evidence.id,
            "concept": evidence.candidate_concept,
            "summary": evidence.normalized_summary,
            "original": evidence.original_text,
            "evidence_type": evidence.evidence_type.value,
        },
        "affected_patterns": affected,
        "warning": "Deleting this reflection removes its graph links before DNA is recalculated.",
    }


@vault_router.delete("/vault/{user_id}/evidence/{evidence_id}/with-impact")
def delete_evidence_with_impact(user_id: str, evidence_id: str, db: Session = Depends(get_db)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence or evidence.user_id != user_id:
        raise HTTPException(404, "Evidence not found")

    links = db.scalars(
        select(PatternEvidence).where(PatternEvidence.evidence_id == evidence.id)
    ).all()
    impacted_ids = list(dict.fromkeys(link.pattern_id for link in links))
    before = [
        snap for pid in impacted_ids
        if (snap := _pattern_snapshot(db, user_id, pid)) is not None
    ]

    deleted_evidence = {
        "id": evidence.id,
        "concept": evidence.candidate_concept,
        "summary": evidence.normalized_summary,
        "original": evidence.original_text,
    }
    db.delete(evidence)
    db.commit()
    recompute_patterns(db, user_id)

    after = [
        snap for pid in impacted_ids
        if (snap := _pattern_snapshot(db, user_id, pid)) is not None
    ]
    after_by_id = {item["pattern_id"]: item for item in after}
    changes = []
    for old in before:
        new = after_by_id.get(old["pattern_id"])
        if not new:
            continue
        changes.append(
            {
                "pattern_id": old["pattern_id"],
                "before": old,
                "after": new,
                "changed": (
                    old["pattern_status"] != new["pattern_status"]
                    or old["support_count"] != new["support_count"]
                    or old["contradiction_count"] != new["contradiction_count"]
                ),
                "message": _change_message(old, new),
                "ownership_preserved": (
                    old["user_label"] == new["user_label"]
                    and old["strand_status"] == new["strand_status"]
                ),
            }
        )

    return {
        "deleted": deleted_evidence,
        "recalculated": True,
        "changes": changes,
        "principle": "The deleted reflection is no longer available to support or challenge DNA.",
    }
