from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import AIProvider, get_ai_provider
from app.models.entities import (
    DNAExperience,
    DNAStrand,
    Evidence,
    EvidenceStrength,
    EvidenceType,
    Pattern,
    PatternEvidence,
    PatternStatus,
    StrandStatus,
)
from app.services.evidence.guard import assert_dna_eligible
from app.services.safety import assert_safe_for_dna


def _flatten(value):
    if isinstance(value, dict):
        return " ".join(f"{k} {_flatten(v)}" for k, v in value.items())
    if isinstance(value, list):
        return " ".join(_flatten(v) for v in value)
    return str(value)


def extract_evidence(
    db: Session,
    experience: DNAExperience,
    provider: AIProvider | None = None,
):
    """Extract structured evidence through a pluggable AI provider.

    Purpose, consent, dna_allowed, and safety are checked before any provider
    receives the reflection. Blocked text cannot create downstream evidence.
    """
    assert_dna_eligible(experience)
    text = _flatten(experience.raw_response).strip()
    if not text:
        return []
    assert_safe_for_dna(text)
    provider = provider or get_ai_provider()

    candidates = provider.extract_evidence(text, experience.experience_type.value)
    created: list[Evidence] = []
    for candidate in candidates:
        try:
            evidence_type = EvidenceType(candidate.evidence_type)
            strength = EvidenceStrength(candidate.strength)
        except ValueError:
            continue
        evidence = Evidence(
            user_id=experience.user_id,
            experience_id=experience.id,
            source_type="dna_experience",
            source_reference={"experience_type": experience.experience_type.value, "provider": provider.__class__.__name__},
            candidate_concept=candidate.concept.strip()[:200],
            evidence_type=evidence_type,
            normalized_summary=candidate.summary[:1000],
            original_text=candidate.original_text[:2000],
            strength=strength,
        )
        db.add(evidence)
        created.append(evidence)
    db.flush()
    return created


def _status_for(evs: list[Evidence]) -> PatternStatus:
    supports = [e for e in evs if e.evidence_type == EvidenceType.SUPPORT]
    contradictions = [e for e in evs if e.evidence_type == EvidenceType.CONTRADICT]
    if not supports:
        return PatternStatus.UNKNOWN

    # A single reflection can never become a strong/repeated DNA pattern.
    unique_experiences = {e.experience_id for e in supports if e.experience_id}
    unique_types = {
        (e.source_reference or {}).get("experience_type")
        for e in supports
        if (e.source_reference or {}).get("experience_type")
    }

    if contradictions:
        return PatternStatus.QUESTIONED
    if len(supports) >= 3 and len(unique_experiences) >= 3 and len(unique_types) >= 2:
        return PatternStatus.REPEATED
    return PatternStatus.EMERGING


def recompute_patterns(db: Session, user_id: str):
    items = db.scalars(select(Evidence).where(Evidence.user_id == user_id)).all()
    grouped: dict[str, list[Evidence]] = defaultdict(list)
    for evidence in items:
        # Only evidence created by the self-discovery pipeline is eligible.
        assert_dna_eligible(evidence)
        grouped[evidence.candidate_concept].append(evidence)

    existing = {p.ai_label: p for p in db.scalars(select(Pattern).where(Pattern.user_id == user_id)).all()}

    # Patterns whose evidence was deleted are reset instead of retaining stale state.
    for label, pattern in existing.items():
        if label not in grouped and pattern.status != PatternStatus.REJECTED:
            pattern.status = PatternStatus.UNKNOWN
            pattern.support_count = 0
            pattern.contradiction_count = 0

    for concept, evs in grouped.items():
        support = sum(e.evidence_type == EvidenceType.SUPPORT for e in evs)
        contra = sum(e.evidence_type == EvidenceType.CONTRADICT for e in evs)
        status = _status_for(evs)

        pattern = existing.get(concept)
        if not pattern:
            pattern = Pattern(
                user_id=user_id,
                ai_label=concept,
                description=f"Possible recurring clue around {concept}.",
            )
            db.add(pattern)
            db.flush()
            existing[concept] = pattern

        # A user rejection has higher authority than automatic recomputation.
        if pattern.status != PatternStatus.REJECTED:
            pattern.status = status
        pattern.support_count = support
        pattern.contradiction_count = contra

        for link in db.scalars(select(PatternEvidence).where(PatternEvidence.pattern_id == pattern.id)).all():
            db.delete(link)
        db.flush()
        for evidence in evs:
            db.add(
                PatternEvidence(
                    pattern_id=pattern.id,
                    evidence_id=evidence.id,
                    relationship=evidence.evidence_type,
                )
            )

        strand = db.scalar(
            select(DNAStrand).where(DNAStrand.user_id == user_id, DNAStrand.pattern_id == pattern.id)
        )
        if not strand and pattern.status not in {PatternStatus.UNKNOWN, PatternStatus.REJECTED}:
            db.add(
                DNAStrand(
                    user_id=user_id,
                    pattern_id=pattern.id,
                    ai_original_label=concept,
                    status=StrandStatus.AI_PROPOSED,
                )
            )
        elif strand and pattern.status == PatternStatus.QUESTIONED and strand.status == StrandStatus.AI_PROPOSED:
            strand.status = StrandStatus.QUESTIONED

    db.commit()
    return db.scalars(select(Pattern).where(Pattern.user_id == user_id)).all()
