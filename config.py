"""Paths and environment — load `.env` from the project root."""

import os
import sys
from datetime import date, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_ROOT / ".env")


_load_env()


def _resolved_path(env_key: str, default_relative: str) -> str:
    raw = os.environ.get(env_key, default_relative).strip()
    if not raw:
        raw = default_relative
    p = Path(raw)
    if not p.is_absolute():
        p = _ROOT / p
    return str(p.resolve())


DATA_DIR = _resolved_path("SFBC_INPUT_DIR", "docs/input_docs/2025")
OUTPUT_DIR = _resolved_path("SFBC_OUTPUT_DIR", "output")
OUTPUT_PREFIX = Path(OUTPUT_DIR).name or "output"


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    print(f"Warning: could not parse date {raw!r}", file=sys.stderr)
    return None


# Default analysis window: full calendar year of "today" (when neither date is set in .env)
_today_y = date.today().year
_default_start = date(_today_y, 1, 1)
_default_end = date(_today_y, 12, 31)
_raw_start = os.environ.get("SFBC_ANALYSIS_START", "").strip()
_raw_end = os.environ.get("SFBC_ANALYSIS_END", "").strip()
_parsed_start = _parse_date(_raw_start) if _raw_start else None
_parsed_end = _parse_date(_raw_end) if _raw_end else None

if _parsed_start is not None and _parsed_end is not None:
    ANALYSIS_START, ANALYSIS_END = _parsed_start, _parsed_end
elif _parsed_start is not None:
    ANALYSIS_START = _parsed_start
    ANALYSIS_END = date(_parsed_start.year, 12, 31)
elif _parsed_end is not None:
    ANALYSIS_END = _parsed_end
    ANALYSIS_START = date(_parsed_end.year, 1, 1)
else:
    ANALYSIS_START, ANALYSIS_END = _default_start, _default_end

if ANALYSIS_START > ANALYSIS_END:
    raise ValueError(
        f"SFBC_ANALYSIS_START ({ANALYSIS_START}) must be on or before SFBC_ANALYSIS_END ({ANALYSIS_END})"
    )


def _period_label(start: date, end: date) -> str:
    if start == date(start.year, 1, 1) and end == date(start.year, 12, 31) and start.year == end.year:
        return str(start.year)
    if start.year == end.year:
        return f"{start.strftime('%b %d')}-{end.strftime('%b %d, %Y')}"
    return f"{start.isoformat()}-{end.isoformat()}"


REPORT_PERIOD_LABEL = _period_label(ANALYSIS_START, ANALYSIS_END)
