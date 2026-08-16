from app.core.purpose import ensure_self_discovery_purpose


def assert_dna_eligible(record) -> None:
    """Hard boundary for DNA processing.

    SELF_DISCOVERY purpose, explicit analysis consent, and dna_allowed are
    independent boundaries. A false dna_allowed flag is always authoritative,
    regardless of the record's concrete class or purpose value.
    """
    if getattr(record, "dna_allowed", True) is False:
        raise PermissionError("dna_allowed=false blocks DNA evidence processing.")
    ensure_self_discovery_purpose(record.purpose)
    if hasattr(record, "consent_for_analysis") and not record.consent_for_analysis:
        raise PermissionError("DNA analysis consent is required before evidence extraction.")
