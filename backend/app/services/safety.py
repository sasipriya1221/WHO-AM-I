import re
from dataclasses import dataclass


_HIGH_RISK_PATTERNS = (
    re.compile(r"\b(?:kill|hurt|harm)\s+myself\b", re.IGNORECASE),
    re.compile(r"\bsuicid(?:e|al)\b", re.IGNORECASE),
    re.compile(r"\bself[\s-]?harm\b", re.IGNORECASE),
)


class SafetyViolationError(PermissionError):
    """Raised when text must not enter the DNA evidence pipeline."""


@dataclass(frozen=True)
class SafetyAssessment:
    allow_dna_processing: bool
    risk: str


def assess_dna_text(text: str) -> SafetyAssessment:
    normalized = " ".join(str(text).split())
    high_risk = any(pattern.search(normalized) for pattern in _HIGH_RISK_PATTERNS)
    return SafetyAssessment(
        allow_dna_processing=not high_risk,
        risk="high" if high_risk else "normal",
    )


def assert_safe_for_dna(text: str) -> None:
    if not assess_dna_text(text).allow_dna_processing:
        raise SafetyViolationError(
            "High-risk text is blocked from DNA evidence processing."
        )
