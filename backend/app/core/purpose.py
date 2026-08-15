from enum import Enum

class DataPurpose(str, Enum):
    ENTERTAINMENT = "entertainment"
    SELF_DISCOVERY = "self_discovery"
    COMPASS = "compass"
    SAFETY = "safety"

class PurposeViolationError(PermissionError):
    pass

def ensure_self_discovery_purpose(purpose: str | DataPurpose) -> None:
    value = purpose.value if isinstance(purpose, DataPurpose) else purpose
    if value != DataPurpose.SELF_DISCOVERY.value:
        raise PurposeViolationError("Only explicit self-discovery data can enter Happiness DNA evidence.")
