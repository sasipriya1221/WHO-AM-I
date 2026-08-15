from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import *
from app.schemas.common import *
from app.services.dna.engine import extract_evidence,recompute_patterns
from app.core.purpose import DataPurpose
router=APIRouter(prefix="/api/v1")
def user_or_404(db,user_id):
    u=db.get(User,user_id)
    if not u: raise HTTPException(404,"User not found")
    return u
@router.post("/users/demo")
def create_demo(payload:DemoUserCreate,db:Session=Depends(get_db)):
    existing=db.scalar(select(User).where(User.email==payload.email))
    if existing:return {"id":existing.id,"display_name":existing.display_name,"phase":existing.current_phase.value}
    u=User(email=payload.email,display_name=payload.display_name);db.add(u);db.commit();db.refresh(u);return {"id":u.id,"display_name":u.display_name,"phase":u.current_phase.value}
@router.post("/mirror/{user_id}/interests")
def add_interest(user_id:str,payload:InterestCreate,db:Session=Depends(get_db)):
    user_or_404(db,user_id);i=MirrorInterest(user_id=user_id,category=payload.category,name=payload.name,purpose=DataPurpose.ENTERTAINMENT.value,dna_allowed=False);db.add(i);db.commit();db.refresh(i);return {"id":i.id,"category":i.category,"name":i.name,"purpose":i.purpose,"dna_allowed":i.dna_allowed}
@router.get("/mirror/{user_id}/game")
def get_game(user_id:str,db:Session=Depends(get_db)):
    ints=db.scalars(select(MirrorInterest).where(MirrorInterest.user_id==user_id)).all()
    if not ints:return {"title":"Quick hello","question":"Tell Mirror one series, game, or sport you enjoy.","options":[]}
    name=ints[0].name;lower=name.lower()
    if "throne" in lower:return {"title":"Your GOT challenge","question":"What are the words of House Stark?","options":["Winter is Coming","Fire and Blood","Hear Me Roar"],"answer":"Winter is Coming","note":"Entertainment only — never DNA evidence."}
    if "angry" in lower:return {"title":"Angry Birds-inspired puzzle","question":"A target is behind a tall wall. Which launch is most likely to clear it?","options":["Low angle","Medium angle","High arc"],"answer":"High arc","note":"Entertainment only — never DNA evidence."}
    return {"title":f"A little {name} moment","question":f"What do you enjoy most about {name}?","options":["The challenge","The story","The people","Just fun"],"note":"Entertainment only — never DNA evidence."}
@router.post("/dna/{user_id}/consent")
def dna_consent(user_id:str,payload:DNAConsent,db:Session=Depends(get_db)):
    u=user_or_404(db,user_id);u.dna_consent=payload.consent
    if payload.consent:u.current_phase=Phase.DNA
    db.commit();return {"consent":u.dna_consent,"phase":u.current_phase.value}
@router.post("/dna/{user_id}/experiences")
def create_experience(user_id:str,payload:ExperienceCreate,db:Session=Depends(get_db)):
    u=user_or_404(db,user_id)
    if not u.dna_consent:raise HTTPException(403,"DNA consent required")
    if not payload.consent_for_analysis:raise HTTPException(400,"Use off-the-record mode for non-analysed experiences")
    try:et=ExperienceType(payload.experience_type);mode=InputMode(payload.input_mode)
    except ValueError as e:raise HTTPException(422,str(e))
    x=DNAExperience(user_id=user_id,experience_type=et,input_mode=mode,raw_response=payload.response,consent_for_analysis=True);db.add(x);db.flush();created=extract_evidence(db,x);db.commit();recompute_patterns(db,user_id);return {"experience_id":x.id,"evidence_created":len(created)}
@router.get("/dna/{user_id}/patterns")
def patterns(user_id:str,db:Session=Depends(get_db)):
    return [{"id":p.id,"label":p.ai_label,"status":p.status.value,"support":p.support_count,"contradict":p.contradiction_count} for p in db.scalars(select(Pattern).where(Pattern.user_id==user_id)).all()]
@router.get("/dna/{user_id}/patterns/{pattern_id}/evidence")
def pattern_evidence(user_id:str,pattern_id:str,db:Session=Depends(get_db)):
    p=db.get(Pattern,pattern_id)
    if not p or p.user_id!=user_id:raise HTTPException(404,"Pattern not found")
    support=[];contradict=[]
    for link in db.scalars(select(PatternEvidence).where(PatternEvidence.pattern_id==pattern_id)).all():
        e=db.get(Evidence,link.evidence_id);item={"id":e.id,"summary":e.normalized_summary,"original":e.original_text,"experience_id":e.experience_id};(support if link.relationship==EvidenceType.SUPPORT else contradict).append(item)
    return {"pattern":p.ai_label,"status":p.status.value,"supporting":support,"contradicting":contradict}
@router.get("/dna/{user_id}/strands")
def strands(user_id:str,db:Session=Depends(get_db)):
    return [{"id":s.id,"pattern_id":s.pattern_id,"ai_label":s.ai_original_label,"user_label":s.user_label,"status":s.status.value} for s in db.scalars(select(DNAStrand).where(DNAStrand.user_id==user_id)).all()]
@router.patch("/dna/{user_id}/strands/{strand_id}")
def rename_strand(user_id:str,strand_id:str,payload:StrandRename,db:Session=Depends(get_db)):
    s=db.get(DNAStrand,strand_id)
    if not s or s.user_id!=user_id:raise HTTPException(404,"Strand not found")
    s.user_label=payload.user_label;s.status=StrandStatus.USER_DEFINED;db.commit();return {"id":s.id,"user_label":s.user_label,"status":s.status.value}
@router.post("/compass/{user_id}/chapters")
def create_chapter(user_id:str,payload:ChapterCreate,db:Session=Depends(get_db)):
    u=user_or_404(db,user_id);u.current_phase=Phase.COMPASS;c=LifeChapter(user_id=user_id,title=payload.title,description=payload.description);db.add(c);db.commit();db.refresh(c);return {"id":c.id,"title":c.title}
@router.post("/compass/{user_id}/reflect")
def compass_reflect(user_id:str,payload:CompassReflect,db:Session=Depends(get_db)):
    chapter=db.get(LifeChapter,payload.chapter_id)
    if not chapter or chapter.user_id!=user_id:raise HTTPException(404,"Chapter not found")
    eligible=db.scalars(select(DNAStrand).where(DNAStrand.user_id==user_id,DNAStrand.status==StrandStatus.USER_DEFINED)).all()
    if not eligible:return {"type":"fog","text":"Some parts of this road are still unclear. Define at least one DNA strand in your own words before Compass uses it."}
    label=eligible[0].user_label or eligible[0].ai_original_label;return {"type":"question","strand":label,"text":f"You defined ‘{label}’ as meaningful. Does the road you're describing leave room for it — and is that trade-off intentional?","note":"Compass notices and questions. It never recommends a decision."}
@router.get("/vault/{user_id}")
def vault(user_id:str,db:Session=Depends(get_db)):
    return {"entertainment":[{"id":i.id,"label":i.name,"purpose":i.purpose} for i in db.scalars(select(MirrorInterest).where(MirrorInterest.user_id==user_id)).all()],"self_discovery":[{"id":e.id,"label":e.candidate_concept,"summary":e.normalized_summary} for e in db.scalars(select(Evidence).where(Evidence.user_id==user_id)).all()],"dna":[{"id":s.id,"label":s.user_label or s.ai_original_label,"status":s.status.value} for s in db.scalars(select(DNAStrand).where(DNAStrand.user_id==user_id)).all()]}
@router.delete("/vault/{user_id}/evidence/{evidence_id}")
def delete_evidence(user_id:str,evidence_id:str,db:Session=Depends(get_db)):
    e=db.get(Evidence,evidence_id)
    if not e or e.user_id!=user_id:raise HTTPException(404,"Evidence not found")
    db.delete(e);db.commit();recompute_patterns(db,user_id);return {"deleted":evidence_id,"recalculated":True}
@router.post("/safety/check")
def safety(payload:SafetyCheck):
    text=payload.text.lower();high=any(x in text for x in ["kill myself","suicide","self harm","hurt myself"]);return {"allow_dna_processing":not high,"risk":"high" if high else "normal","note":"High-risk content must not become Happiness DNA evidence."}
