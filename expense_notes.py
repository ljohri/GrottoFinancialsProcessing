"""Parse Expense Notes.txt into a lookup dict for major expense annotations."""

import os
import re


def load_expense_notes(path: str) -> dict[str, dict]:
    """Parse Expense Notes.txt and return a dict keyed by normalized description.

    Each entry:
        {
            "short_label": str,   # first non-empty note line (used in pie chart)
            "note":        str,   # full note text
        }

    File format (blocks separated by blank lines):
        <description line> :
        <note text>

        <description line>:
        <note text>
    """
    if not os.path.exists(path):
        return {}

    with open(path, encoding="utf-8") as fh:
        content = fh.read()

    notes: dict[str, dict] = {}

    # Split into blocks separated by one or more blank lines
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            continue

        # First line = description (may have trailing colon/spaces)
        raw_key = lines[0].rstrip(": ").strip()
        # Note text = remaining lines joined
        note_text = " ".join(lines[1:]).strip()
        # Short label = first note line (used in charts)
        short_label = lines[1].strip()

        if raw_key:
            notes[_normalize_key(raw_key)] = {
                "short_label": short_label,
                "note": note_text,
            }

    return notes


def _normalize_key(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for fuzzy matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def lookup_note(description: str, notes: dict[str, dict]) -> dict | None:
    """Find the best matching note for a transaction description."""
    norm = _normalize_key(description)
    # Exact match first
    if norm in notes:
        return notes[norm]
    # Substring match: return first note whose key is contained in the description
    for key, val in notes.items():
        if key in norm or norm in key:
            return val
    return None
