from pydantic import BaseModel,Field
from typing import Any
class DemoUserCreate(BaseModel): display_name:str="Maya"; email:str="maya@example.com"
class InterestCreate(BaseModel): category:str; name:str
class DNAConsent(BaseModel): consent:bool
class ExperienceCreate(BaseModel): experience_type:str; input_mode:str="text"; response:dict[str,Any]; consent_for_analysis:bool=True
class StrandRename(BaseModel): user_label:str=Field(min_length=1,max_length=200)
class ChapterCreate(BaseModel): title:str; description:str|None=None
class CompassReflect(BaseModel): chapter_id:str; strand_id:str|None=None; focus:dict[str,int]={}
class SafetyCheck(BaseModel): text:str
