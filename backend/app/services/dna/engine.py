from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.services.evidence.guard import assert_dna_eligible
from app.models.entities import DNAExperience,Evidence,EvidenceType,EvidenceStrength,Pattern,PatternStatus,PatternEvidence,DNAStrand,StrandStatus

CONCEPTS={"autonomy":["freedom","choice","control","independent","independence","trapped","my own"],"connection":["family","friend","friends","together","people","understood","share","shared"],"learning":["learn","learning","study","solve","figuring","difficult","challenge","curious"],"creation":["build","create","creating","project","made","design","idea"],"recognition":["praise","recognized","recognition","award","win","winning","status","admire"],"persistence":["didn't give up","did not give up","kept going","persist","retry","again"],"security":["stable","stability","secure","security","safe","salary","money"]}
NEGATORS=["not","didn't","did not","without","less","doesn't","does not"]
def _flatten(value):
    if isinstance(value,dict): return " ".join(f"{k} {_flatten(v)}" for k,v in value.items())
    if isinstance(value,list): return " ".join(_flatten(v) for v in value)
    return str(value)
def extract_evidence(db:Session,experience:DNAExperience):
    assert_dna_eligible(experience); text=_flatten(experience.raw_response).lower(); created=[]
    for concept,kws in CONCEPTS.items():
        hits=[k for k in kws if k in text]
        if not hits: continue
        contradict=any(n in text for n in NEGATORS) and any(k in text for k in hits)
        e=Evidence(user_id=experience.user_id,experience_id=experience.id,source_type="dna_experience",source_reference={"experience_type":experience.experience_type.value},candidate_concept=concept,evidence_type=EvidenceType.CONTRADICT if contradict else EvidenceType.SUPPORT,normalized_summary=f"{concept.title()} signal from {experience.experience_type.value.replace('_',' ')}",original_text=text[:2000],strength=EvidenceStrength.MODERATE)
        db.add(e); created.append(e)
    db.flush(); return created
def recompute_patterns(db:Session,user_id:str):
    items=db.scalars(select(Evidence).where(Evidence.user_id==user_id)).all(); grouped=defaultdict(list)
    for e in items: grouped[e.candidate_concept].append(e)
    existing={p.ai_label:p for p in db.scalars(select(Pattern).where(Pattern.user_id==user_id)).all()}
    for concept,evs in grouped.items():
        support=sum(e.evidence_type==EvidenceType.SUPPORT for e in evs); contra=sum(e.evidence_type==EvidenceType.CONTRADICT for e in evs)
        status=PatternStatus.UNKNOWN if support==0 else PatternStatus.QUESTIONED if contra>0 and support<=contra+1 else PatternStatus.REPEATED if support>=3 and contra==0 else PatternStatus.EMERGING
        p=existing.get(concept)
        if not p: p=Pattern(user_id=user_id,ai_label=concept,description=f"Possible recurring clue around {concept}."); db.add(p); db.flush(); existing[concept]=p
        p.status=status; p.support_count=support; p.contradiction_count=contra
        for l in db.scalars(select(PatternEvidence).where(PatternEvidence.pattern_id==p.id)).all(): db.delete(l)
        db.flush()
        for e in evs: db.add(PatternEvidence(pattern_id=p.id,evidence_id=e.id,relationship=e.evidence_type))
        strand=db.scalar(select(DNAStrand).where(DNAStrand.user_id==user_id,DNAStrand.pattern_id==p.id))
        if not strand and status!=PatternStatus.UNKNOWN: db.add(DNAStrand(user_id=user_id,pattern_id=p.id,ai_original_label=concept,status=StrandStatus.AI_PROPOSED))
    db.commit(); return db.scalars(select(Pattern).where(Pattern.user_id==user_id)).all()
