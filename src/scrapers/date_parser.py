import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import structlog
from dateutil import parser as dt_parser

from config.settings import settings

logger = structlog.get_logger(__name__)

LAST_RUN_FILE = settings.DATA_PROCESSED_DIR / "last_run.json"


def get_last_run_timestamp() -> datetime:
    """Read last successful crawl timestamp from data/processed/last_run.json or default to now-24h."""
    if LAST_RUN_FILE.exists():
        try:
            with open(LAST_RUN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                ts_str = data.get("last_run_utc")
                if ts_str:
                    return datetime.fromisoformat(ts_str)
        except Exception as e:
            logger.warning("Failed to read last_run.json, using 24h fallback", error=str(e))
    # Default fallback: 24 hours ago
    return datetime.now(timezone.utc) - timedelta(hours=24)


def update_last_run_timestamp() -> None:
    """Save current UTC timestamp to data/processed/last_run.json upon successful pipeline run."""
    settings.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"last_run_utc": datetime.now(timezone.utc).isoformat()}
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info("Updated last run timestamp", timestamp=payload["last_run_utc"])


def parse_relative_date(date_str: str) -> Optional[datetime]:
    """Parse relative time expressions (e.g. '2 hours ago', 'yesterday', '15m ago', '3d ago')."""
    now = datetime.now(timezone.utc)
    s = date_str.lower().strip()

    if "just now" in s or "moments ago" in s:
        return now

    if "yesterday" in s:
        return now - timedelta(days=1)

    # Match numeric relative strings e.g. "3 hours ago", "15 mins ago", "2d ago", "5h ago"
    match = re.search(r"(\d+)\s*(sec|s|min|m|hour|h|day|d|week|w)s?\s*(ago)?", s)
    if match:
        val = int(match.group(1))
        unit = match.group(2)

        if unit in ("sec", "s"):
            return now - timedelta(seconds=val)
        elif unit in ("min", "m"):
            return now - timedelta(minutes=val)
        elif unit in ("hour", "h"):
            return now - timedelta(hours=val)
        elif unit in ("day", "d"):
            return now - timedelta(days=val)
        elif unit in ("week", "w"):
            return now - timedelta(weeks=val)

    return None


def extract_date_from_html_heuristics(raw_html: str) -> Tuple[Optional[datetime], Optional[str]]:
    """Search HTML for <time> tags, meta tags, and JSON-LD datePublished."""
    if not raw_html:
        return None, None

    # Heuristic 1: <time datetime="..."> tag
    time_match = re.search(r'<time[^>]*datetime=["\']([^"\']+)["\']', raw_html, re.I)
    if time_match:
        try:
            parsed = dt_parser.parse(time_match.group(1))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed, "HTML <time datetime> tag"
        except Exception:
            pass

    # Heuristic 2: Meta tags (article:published_time, datePublished)
    meta_match = re.search(
        r'<meta[^>]*(?:property|name)=["\'](?:article:published_time|datePublished|pubdate)["\'][^>]*content=["\']([^"\']+)["\']',
        raw_html,
        re.I,
    )
    if meta_match:
        try:
            parsed = dt_parser.parse(meta_match.group(1))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed, "Meta article:published_time tag"
        except Exception:
            pass

    # Heuristic 3: JSON-LD "datePublished": "..."
    jsonld_match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw_html, re.I)
    if jsonld_match:
        try:
            parsed = dt_parser.parse(jsonld_match.group(1))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed, "JSON-LD datePublished tag"
        except Exception:
            pass

    return None, None


def normalize_date(
    date_str: Optional[str],
    raw_html: Optional[str] = None,
    record_id: str = "unknown",
) -> datetime:
    """
    Normalize arbitrary date representations into an absolute UTC datetime object.
    Applies intelligent heuristic fallbacks if date_str is missing or malformed.
    Logs every heuristic fallback used for auditability.
    """
    # 1. Try parsing explicit date_str if provided
    if date_str and isinstance(date_str, str):
        # Try relative date parsing first
        rel_dt = parse_relative_date(date_str)
        if rel_dt:
            return rel_dt

        # Try dateutil absolute date parsing
        try:
            parsed = dt_parser.parse(date_str)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            pass

    # 2. Try HTML heuristic extraction if raw HTML is provided
    if raw_html:
        heur_dt, heur_name = extract_date_from_html_heuristics(raw_html)
        if heur_dt:
            logger.info(
                "Date normalization applied heuristic fallback",
                record_id=record_id,
                heuristic=heur_name,
                resolved_date=heur_dt.isoformat(),
            )
            return heur_dt

    # 3. Fallback: compare against last successful run timestamp
    last_run = get_last_run_timestamp()
    logger.info(
        "Date normalization applied last-run inference fallback",
        record_id=record_id,
        heuristic="last_run_inference",
        resolved_date=last_run.isoformat(),
    )
    return last_run
