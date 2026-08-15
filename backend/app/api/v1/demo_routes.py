from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import (
    DNAExperience,
    DNAStrand,
    Evidence,
    EvidenceStrength,
    EvidenceType,
    ExperienceType,
    InputMode,
    LifeChapter,
    MirrorInterest,
    Pattern,
    Phase,
    User,
)
from app.services.dna.engine import recompute_patterns


demo_router = APIRouter(prefix="/demo", tags=["judge-demo"])


@demo_router.post("/seed")
def seed_judge_demo(db: Session = Depends(get_db)):
    """Create a fresh, deterministic judge-facing golden-path user.

    Seeded evidence deliberately includes three independent autonomy supports
    (enough for Repeated) plus a separate contradictory clue that Challenge can
    retrieve semantically. Entertainment remains purpose-separated.
    """
    token = uuid.uuid4().hex[:10]
    user = User(
        email=f"judge-maya-{token}@demo.local",
        display_name="Maya",
        current_phase=Phase.DNA,
        dna_consent=True,
    )
    db.add(user)
    db.flush()

    interest = MirrorInterest(
        user_id=user.id,
        category="series",
        name="Game of Thrones",
        source="explicit_user",
        purpose="entertainment",
        dna_allowed=False,
    )
    db.add(interest)

    seeded = [
        (
            ExperienceType.EMPTY_ROOM,
            "In my room, I placed control over my own choices closest to me. I want freedom to decide how I work.",
            "Empty Room placed choice and control close to the centre.",
        ),
        (
            ExperienceType.FUTURE_ME,
            "Future me would regret feeling trapped in a life I never chose. I want freedom to make my own decisions.",
            "Future Me expressed concern about being trapped by choices made by others.",
        ),
        (
            ExperienceType.ALTERNATIVE_LIFE,
            "I chose the path with less status but more control over my time and decisions.",
            "Alternative Life preferred control over status.",
        ),
    ]

    experience_ids: list[str] = []
    support_evidence_ids: list[str] = []
    for experience_type, raw, summary in seeded:
        exp = DNAExperience(
            user_id=user.id,
            experience_type=experience_type,
            input_mode=InputMode.TEXT,
            raw_response={"reflection": raw},
            purpose="self_discovery",
            consent_for_analysis=True,
        )
        db.add(exp)
        db.flush()
        evidence = Evidence(
            user_id=user.id,
            experience_id=exp.id,
            source_type="dna_experience",
            source_reference={"experience_type": experience_type.value, "seeded_demo": True},
            purpose="self_discovery",
            candidate_concept="autonomy",
            evidence_type=EvidenceType.SUPPORT,
            normalized_summary=summary,
            original_text=raw,
            strength=EvidenceStrength.MODERATE,
        )
        db.add(evidence)
        db.flush()
        experience_ids.append(exp.id)
        support_evidence_ids.append(evidence.id)

    # This clue is intentionally a different candidate concept so it does not
    # weaken the initial autonomy pattern, but it is available to Challenge's
    # semantic counter-evidence search.
    counter_exp = DNAExperience(
        user_id=user.id,
        experience_type=ExperienceType.REFLECTION,
        input_mode=InputMode.TEXT,
        raw_response={
            "reflection": "Sometimes I actively choose structure and stability over freedom; having every choice open can feel exhausting."
        },
        purpose="self_discovery",
        consent_for_analysis=True,
    )
    db.add(counter_exp)
    db.flush()
    counter = Evidence(
        user_id=user.id,
        experience_id=counter_exp.id,
        source_type="dna_experience",
        source_reference={"experience_type": ExperienceType.REFLECTION.value, "seeded_demo": True},
        purpose="self_discovery",
        candidate_concept="structured_choice",
        evidence_type=EvidenceType.CONTRADICT,
        normalized_summary="In some contexts, Maya chooses structure and stability over maximum freedom.",
        original_text=counter_exp.raw_response["reflection"],
        strength=EvidenceStrength.MODERATE,
    )
    db.add(counter)
    db.commit()

    recompute_patterns(db, user.id)
    pattern = db.scalar(
        select(Pattern).where(Pattern.user_id == user.id, Pattern.ai_label == "autonomy")
    )
    strand = db.scalar(
        select(DNAStrand).where(DNAStrand.user_id == user.id, DNAStrand.pattern_id == pattern.id)
    )
    chapter = LifeChapter(
        user_id=user.id,
        title="Placement",
        description="Applications, interviews, learning, and deciding what kind of first role I want.",
        status="active",
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)

    return {
        "demo": "judge_golden_path",
        "user": {"id": user.id, "display_name": user.display_name},
        "entertainment": {
            "label": interest.name,
            "purpose": interest.purpose,
            "dna_allowed": interest.dna_allowed,
        },
        "experiences": [
            {"id": experience_ids[0], "type": "empty_room", "label": "Empty Room"},
            {"id": experience_ids[1], "type": "future_me", "label": "Future Me"},
            {"id": experience_ids[2], "type": "alternative_life", "label": "Alternative Life"},
        ],
        "pattern": {
            "id": pattern.id,
            "ai_label": pattern.ai_label,
            "status": pattern.status.value,
            "support_count": pattern.support_count,
        },
        "strand": {"id": strand.id, "status": strand.status.value},
        "chapter": {"id": chapter.id, "title": chapter.title},
        "delete_candidate_evidence_id": support_evidence_ids[0],
        "counter_evidence_id": counter.id,
        "sequence": [
            "experience",
            "dna_reveal",
            "challenge",
            "human_rename",
            "compass",
            "delete_evidence",
            "dna_weakens",
        ],
        "principle": "The AI may notice a clue. The user owns the meaning, and deleted evidence loses influence.",
    }
