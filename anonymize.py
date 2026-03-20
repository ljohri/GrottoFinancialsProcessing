"""Redact personal names from transaction descriptions before display."""

import re

# ---------------------------------------------------------------------------
# Static known-name mappings (first initial + ***)
# Order matters: longer/more-specific patterns first.
# ---------------------------------------------------------------------------
_STATIC_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    # Full "First Last" forms found in Chase descriptions
    (re.compile(r"\bRON\s+MILLER\b", re.IGNORECASE), "R***"),
    # Single first names used alone in Chase/PayPal descriptions
    (re.compile(r"\bAvik\b", re.IGNORECASE), "A***"),
]

# Regex to detect "Zelle payment to <Name> <ref>" and anonymize just the name portion.
# The reference token after the name is a mix of letters/digits (no spaces).
_ZELLE_TO = re.compile(
    r"(Zelle payment to\s+)([A-Za-z][A-Za-z\s\-']+?)(\s+[A-Z0-9]{8,})",
    re.IGNORECASE,
)


def _redact_name(name: str) -> str:
    """Return first initial of first word + '***'."""
    name = name.strip()
    if not name:
        return "***"
    return name[0].upper() + "***"


def anonymize(text: str) -> str:
    """Apply all name-redaction rules to a description string."""
    if not text:
        return text

    # Apply static replacements first
    for pattern, replacement in _STATIC_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    # Anonymize "Zelle payment to <Name> <ref>" dynamically
    def _replace_zelle(m: re.Match) -> str:
        prefix = m.group(1)   # "Zelle payment to "
        name = m.group(2)     # the name portion
        ref = m.group(3)      # the ref token (keep as-is for traceability)
        return prefix + _redact_name(name) + ref

    text = _ZELLE_TO.sub(_replace_zelle, text)

    return text


def anonymize_paypal_name(name: str) -> str:
    """Anonymize a PayPal sender name (First Last → F***)."""
    if not name:
        return "***"
    return _redact_name(name)
