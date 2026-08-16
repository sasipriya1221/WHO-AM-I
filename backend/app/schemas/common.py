import unicodedata
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DemoUserCreate(BaseModel):
    display_name: str = "Maya"
    email: str = "maya@example.com"


class InterestCreate(BaseModel):
    category: str
    name: str


class DNAConsent(BaseModel):
    consent: bool


class ExperienceCreate(BaseModel):
    experience_type: str
    input_mode: str = "text"
    response: dict[str, Any]
    consent_for_analysis: bool = True


class StrandRename(BaseModel):
    user_label: str = Field(min_length=1, max_length=200)

    @field_validator("user_label", mode="before")
    @classmethod
    def normalize_user_label(cls, value):
        if not isinstance(value, str):
            return value
        label = value.strip()
        if not label:
            raise ValueError("User label cannot be empty or whitespace only")
        if any(unicodedata.category(character).startswith("C") for character in label):
            raise ValueError("User label cannot contain control characters")
        return label


class ChapterCreate(BaseModel):
    title: str
    description: str | None = None


class CompassReflect(BaseModel):
    chapter_id: str
    strand_id: str | None = None
    focus: dict[str, int] = {}


class SafetyCheck(BaseModel):
    text: str
