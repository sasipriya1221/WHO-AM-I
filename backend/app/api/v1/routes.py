from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.purpose import DataPurpose
from app.database import get_db
from app.models.entities import *
from app.schemas.common import *
from app.services.dna.engine import extract_evidence, recompute_patterns
from app.services.evidence.semantic import support_and_counter_evidence

router = APIRouter(prefix="/api/v1")


def user_or_404(db, user_id):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


def pattern_or_404(db: Session, user_id: str, pattern_id: str) -> Pattern:
    pattern = db.get(Pattern, pattern_id)
    if not pattern or pattern.user_id != user_id:
        raise HTTPException(404, "Pattern not found")
    return pattern


def strand_or_404(db: Session, user_id: str, strand_id: str) -> DNAStrand:
    strand = db.get(DNAStrand, strand_id)
    if not strand or strand.user_id != user_id:
        raise HTTPException(404, "DNA strand not found")
    return strand


@router.post("/users/demo")
def create_demo(payload: DemoUserCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        return {"id": existing.id, "display_name": existing.display_name, "phase": existing.current_phase.value}
    user = User(email=payload.email, display_name=payload.display_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "display_name": user.display_name, "phase": user.current_phase.value}


@router.post("/mirror/{user_id}/interests")
def add_interest(user_id: str, payload: InterestCreate, db: Session = Depends(get_db)):
    user_or_404(db, user_id)
    interest = MirrorInterest(
        user_id=user_id,
        category=payload.category,
        name=payload.name,
        purpose=DataPurpose.ENTERTAINMENT.value,
        dna_allowed=False,
    )
    db.add(interest)
    db.commit()
    db.refresh(interest)
    return {
        "id": interest.id,
        "category": interest.category,
        "name": interest.name,
        "purpose": interest.purpose,
        "dna_allowed": interest.dna_allowed,
    }


@router.get("/mirror/{user_id}/game")
def get_game(user_id: str, db: Session = Depends(get_db)):
    interests = db.scalars(select(MirrorInterest).where(MirrorInterest.user_id == user_id)).all()
    if not interests:
        return {"title": "Quick hello", "question": "Tell Mirror one series, game, or sport you enjoy.", "options": []}
    name = interests[0].name
    lower = name.lower()
    if "throne" in lower:
        return {"title": "Your GOT challenge", "question": "What are the words of House Stark?", "options": ["Winter is Coming", "Fire and Blood", "Hear Me Roar"], "answer": "Winter is Coming", "note": "Entertainment only — never DNA evidence."}
    if "angry" in lower:
        return {"title": "Angry Birds-inspired puzzle", "question": "A target is behind a tall wall. Which launch is most likely to clear it?", "options": ["Low angle", "Medium angle", "High arc"], "answer": "High arc", "note": "Entertainment only — never DNA evidence."}
    return {"title": f"A little {name} moment", "question": f"What do you enjoy most about {name}?", "options": ["The challenge", "The story", "The people", "Just fun"], "note": "Entertainment only — never DNA evidence."}


@router.post("/dna/{user_id}/consent")
def dna_consent(user_id: str, payload: DNAConsent, db: Session = Depends(get_db)):
    user = user_or_404(db, user_id)
    user.dna_consent = payload.consent
    if payload.consent:
        user.current_phase = Phase.DNA
    db.commit()
    return {"consent": user.dna_consent, "phase": user.current_phase.value}


@router.post("/dna/{user_id}/experiences")
def create_experience(user_id: str, payload: ExperienceCreate, db: Session = Depends(get_db)):
    user = user_or_404(db, user_id)
    if not user.dna_consent:
        raise HTTPException(403, "DNA consent required")
    if not payload.consent_for_analysis:
        raise HTTPException(400, "Use off-the-record mode for non-analysed experiences")
    try:
        experience_type = ExperienceType(payload.experience_type)
        input_mode = InputMode(payload.input_mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    experience = DNAExperience(
        user_id=user_id,
        experience_type=experience_type,
        input_mode=input_mode,
        raw_response=payload.response,
        consent_for_analysis=True,
    )
    db.add(experience)
    db.flush()
    try:
        created = extract_evidence(db, experience)
    except (PermissionError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(403, str(exc))
    db.commit()
    recompute_patterns(db, user_id)
    return {"experience_id": experience.id, "evidence_created": len(created)}


@router.get("/dna/{user_id}/patterns")
def patterns(user_id: str, db: Session = Depends(get_db)):
    return [
        {"id": p.id, "label": p.ai_label, "status": p.status.value, "support": p.support_count, "contradict": p.contradiction_count}
        for p in db.scalars(select(Pattern).where(Pattern.user_id == user_id)).all()
    ]


@router.get("/dna/{user_id}/patterns/{pattern_id}/evidence")
@router.get("/dna/{user_id}/patterns/{pattern_id}/why")
def why_pattern(user_id: str, pattern_id: str, db: Session = Depends(get_db)):
    pattern = pattern_or_404(db, user_id, pattern_id)
    support = []
    contradict = []
    for link in db.scalars(select(PatternEvidence).where(PatternEvidence.pattern_id == pattern_id)).all():
        evidence = db.get(Evidence, link.evidence_id)
        if not evidence:
            continue
        item = {"id": evidence.id, "summary": evidence.normalized_summary, "original": evidence.original_text, "experience_id": evidence.experience_id}
        if link.relationship == EvidenceType.SUPPORT:
            support.append(item)
        elif link.relationship == EvidenceType.CONTRADICT:
            contradict.append(item)
    return {"pattern": pattern.ai_label, "status": pattern.status.value, "supporting": support, "contradicting": contradict}


@router.post("/dna/{user_id}/patterns/{pattern_id}/challenge")
def challenge_pattern(user_id: str, pattern_id: str, db: Session = Depends(get_db)):
    pattern = pattern_or_404(db, user_id, pattern_id)
    result = support_and_counter_evidence(db, user_id, f"{pattern.ai_label}. {pattern.description or ''}")
    if result["contradicting"] and pattern.status not in {PatternStatus.REJECTED}:
        pattern.status = PatternStatus.QUESTIONED
        strand = db.scalar(select(DNAStrand).where(DNAStrand.user_id == user_id, DNAStrand.pattern_id == pattern.id))
        if strand and strand.status == StrandStatus.AI_PROPOSED:
            strand.status = StrandStatus.QUESTIONED
        db.commit()
    return {
        "pattern": pattern.ai_label,
        "status": pattern.status.value,
        **result,
        "message": "Here is evidence that supports this clue and evidence that may prove it wrong. You decide what it means.",
    }


@router.post("/dna/{user_id}/patterns/{pattern_id}/not-me")
def reject_pattern(user_id: str, pattern_id: str, db: Session = Depends(get_db)):
    pattern = pattern_or_404(db, user_id, pattern_id)
    pattern.status = PatternStatus.REJECTED
    strand = db.scalar(select(DNAStrand).where(DNAStrand.user_id == user_id, DNAStrand.pattern_id == pattern.id))
    if strand:
        strand.status = StrandStatus.RETIRED
    db.commit()
    return {"pattern_id": pattern.id, "status": pattern.status.value, "message": "Rejected. The AI will not treat this as your identity."}


@router.get("/dna/{user_id}/strands")
def strands(user_id: str, db: Session = Depends(get_db)):
    return [
        {"id": s.id, "pattern_id": s.pattern_id, "ai_label": s.ai_original_label, "user_label": s.user_label, "status": s.status.value}
        for s in db.scalars(select(DNAStrand).where(DNAStrand.user_id == user_id)).all()
    ]


def _rename_strand(db: Session, user_id: str, strand_id: str, payload: StrandRename):
    strand = strand_or_404(db, user_id, strand_id)
    strand.user_label = payload.user_label
    strand.status = StrandStatus.USER_DEFINED
    db.commit()
    return {"id": strand.id, "ai_label": strand.ai_original_label, "user_label": strand.user_label, "status": strand.status.value}


@router.patch("/dna/{user_id}/strands/{strand_id}")
def rename_strand_legacy(user_id: str, strand_id: str, payload: StrandRename, db: Session = Depends(get_db)):
    return _rename_strand(db, user_id, strand_id, payload)


@router.post("/dna/{user_id}/strands/{strand_id}/rename")
def rename_strand(user_id: str, strand_id: str, payload: StrandRename, db: Session = Depends(get_db)):
    return _rename_strand(db, user_id, strand_id, payload)


@router.get("/dna/{user_id}/strands/{strand_id}/blind-spot")
def blind_spot(user_id: str, strand_id: str, db: Session = Depends(get_db)):
    strand = strand_or_404(db, user_id, strand_id)
    pattern = db.get(Pattern, strand.pattern_id) if strand.pattern_id else None
    ai_label = strand.ai_original_label or (pattern.ai_label if pattern else "this pattern")
    pattern_status = pattern.status.value if pattern else "unknown"
    support_count = pattern.support_count if pattern else 0
    contradiction_count = pattern.contradiction_count if pattern else 0

    if strand.status == StrandStatus.RETIRED or pattern_status == PatternStatus.REJECTED.value:
        raise HTTPException(409, "Rejected strands do not become Blind Spot or Compass material.")

    if strand.status == StrandStatus.USER_DEFINED:
        user_label = strand.user_label or ai_label
        question = (
            f"The AI first called this ‘{ai_label}’. You defined it as ‘{user_label}’. "
            "What does your wording capture that the AI's label missed?"
        )
        if pattern_status == PatternStatus.QUESTIONED.value:
            question = (
                f"The AI first called this ‘{ai_label}’, and conflicting clues tested that label. "
                f"You chose ‘{user_label}’. What changes when you use your words instead of the AI's?"
            )
        return {
            "stage": "blind_spot",
            "ownership_state": "user_defined",
            "ai_label": ai_label,
            "user_label": user_label,
            "pattern_status": pattern_status,
            "support_count": support_count,
            "contradiction_count": contradiction_count,
            "question": question,
            "bridge_text": "Carry your interpretation—not the AI's label—into Compass.",
            "can_enter_compass": True,
            "boundary": "Blind Spot reflects a tension. It does not decide what the tension means.",
        }

    if strand.status == StrandStatus.QUESTIONED or pattern_status == PatternStatus.QUESTIONED.value:
        return {
            "stage": "blind_spot",
            "ownership_state": "ai_challenged",
            "ai_label": ai_label,
            "user_label": None,
            "pattern_status": pattern_status,
            "support_count": support_count,
            "contradiction_count": contradiction_count,
            "question": f"‘{ai_label}’ met conflicting clues. In which situations does it fit, and in which situations does it not?",
            "bridge_text": "Before Compass uses this, define the part that feels true in your own words.",
            "can_enter_compass": False,
            "boundary": "The AI can surface the contradiction. Only you can interpret it.",
        }

    return {
        "stage": "blind_spot",
        "ownership_state": "ai_hypothesis",
        "ai_label": ai_label,
        "user_label": None,
        "pattern_status": pattern_status,
        "support_count": support_count,
        "contradiction_count": contradiction_count,
        "question": f"The AI noticed ‘{ai_label}’. Before carrying it forward, what part of that label feels incomplete or too simple?",
        "bridge_text": "Ask the AI to prove this clue wrong or define it before Compass uses it.",
        "can_enter_compass": False,
        "boundary": "An AI hypothesis is not a user identity.",
    }


@router.post("/compass/{user_id}/chapters")
def create_chapter(user_id: str, payload: ChapterCreate, db: Session = Depends(get_db)):
    user = user_or_404(db, user_id)
    user.current_phase = Phase.COMPASS
    chapter = LifeChapter(user_id=user_id, title=payload.title, description=payload.description)
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return {"id": chapter.id, "title": chapter.title}


@router.post("/compass/{user_id}/reflect")
def compass_reflect(user_id: str, payload: CompassReflect, db: Session = Depends(get_db)):
    chapter = db.get(LifeChapter, payload.chapter_id)
    if not chapter or chapter.user_id != user_id:
        raise HTTPException(404, "Chapter not found")

    strand = None
    if payload.strand_id:
        candidate = strand_or_404(db, user_id, payload.strand_id)
        if candidate.status != StrandStatus.USER_DEFINED:
            raise HTTPException(409, "Compass only uses strands defined by the user.")
        strand = candidate
    else:
        strand = db.scalar(select(DNAStrand).where(DNAStrand.user_id == user_id, DNAStrand.status == StrandStatus.USER_DEFINED))

    if not strand:
        return {
            "type": "fog",
            "text": "Some parts of this road are still unclear. Define at least one DNA strand in your own words before Compass uses it.",
            "ownership_state": "none",
            "note": "Compass refuses to use an unconfirmed AI hypothesis.",
        }

    label = strand.user_label or strand.ai_original_label
    return {
        "type": "question",
        "strand_id": strand.id,
        "strand": label,
        "ownership_state": "user_defined",
        "ai_original_label": strand.ai_original_label,
        "user_defined_label": label,
        "chapter": chapter.title,
        "text": f"You defined ‘{label}’ as meaningful. In this chapter—‘{chapter.title}’—where does your current road make room for it, and where does it not? Is that trade-off intentional?",
        "note": "Compass notices, compares, questions, and remembers. It never recommends a decision.",
        "boundary": "AI notices the road. You keep the steering wheel.",
    }


@router.get("/vault/{user_id}")
def vault(user_id: str, db: Session = Depends(get_db)):
    return {
        "entertainment": [{"id": i.id, "label": i.name, "purpose": i.purpose} for i in db.scalars(select(MirrorInterest).where(MirrorInterest.user_id == user_id)).all()],
        "self_discovery": [{"id": e.id, "label": e.candidate_concept, "summary": e.normalized_summary} for e in db.scalars(select(Evidence).where(Evidence.user_id == user_id)).all()],
        "dna": [{"id": s.id, "label": s.user_label or s.ai_original_label, "status": s.status.value} for s in db.scalars(select(DNAStrand).where(DNAStrand.user_id == user_id)).all()],
    }


@router.delete("/vault/{user_id}/evidence/{evidence_id}")
def delete_evidence(user_id: str, evidence_id: str, db: Session = Depends(get_db)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence or evidence.user_id != user_id:
        raise HTTPException(404, "Evidence not found")
    db.delete(evidence)
    db.commit()
    recompute_patterns(db, user_id)
    return {"deleted": evidence_id, "recalculated": True}


@router.post("/safety/check")
def safety(payload: SafetyCheck):
    text = payload.text.lower()
    high = any(x in text for x in ["kill myself", "suicide", "self harm", "hurt myself"])
    return {"allow_dna_processing": not high, "risk": "high" if high else "normal", "note": "High-risk content must not become Happiness DNA evidence."}
