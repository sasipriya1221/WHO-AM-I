from app.core.purpose import ensure_self_discovery_purpose

def assert_dna_eligible(record) -> None:
    """Hard boundary: only SELF_DISCOVERY records may enter DNA processing."""
    ensure_self_discovery_purpose(record.purpose)
    if getattr(record, "dna_allowed", False) is False and record.__class__.__name__.startswith("Mirror"):
        raise PermissionError("Mirror entertainment data is never DNA evidence.")
