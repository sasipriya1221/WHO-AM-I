from app.core.purpose import ensure_self_discovery_purpose


def assert_dna_eligible(record) -> None:
    """Hard boundary for DNA processing.

    Only SELF_DISCOVERY records are permitted. DNA experiences additionally
    require explicit analysis consent. Mirror records are always rejected.
    """
    ensure_self_discovery_purpose(record.purpose)
    if record.__class__.__name__.startswith("Mirror"):
        raise PermissionError("Mirror entertainment data is never DNA evidence.")
    if hasattr(record, "consent_for_analysis") and not record.consent_for_analysis:
        raise PermissionError("DNA analysis consent is required before evidence extraction.")
