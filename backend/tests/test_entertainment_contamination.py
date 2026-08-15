import pytest
from app.core.purpose import DataPurpose,PurposeViolationError
from app.models import MirrorInterest,Pattern,PatternStatus,User
from app.services.evidence.guard import assert_dna_eligible

def test_mirror_entertainment_cannot_become_dna_evidence_or_change_patterns(db):
    user=User(email="maya@example.com");db.add(user);db.flush();pattern=Pattern(user_id=user.id,ai_label="Challenge Seeking",status=PatternStatus.UNKNOWN,support_count=0,contradiction_count=0);db.add(pattern);interest=MirrorInterest(user_id=user.id,category="game",name="Angry Birds");db.add(interest);db.commit();before=(pattern.status,pattern.support_count,pattern.contradiction_count);assert interest.purpose==DataPurpose.ENTERTAINMENT.value;assert interest.dna_allowed is False
    with pytest.raises((PurposeViolationError,PermissionError)):assert_dna_eligible(interest)
    db.refresh(pattern);after=(pattern.status,pattern.support_count,pattern.contradiction_count);assert after==before;assert pattern.status==PatternStatus.UNKNOWN;assert pattern.support_count==0;assert pattern.contradiction_count==0
