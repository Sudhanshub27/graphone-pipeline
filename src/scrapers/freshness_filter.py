from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
import structlog

logger = structlog.get_logger(__name__)


def is_within_freshness_window(dt: datetime, max_age_hours: int = 24) -> bool:
    """Check if datetime is within the specified freshness window (default: 24 hours)."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(hours=max_age_hours)
    return dt >= cutoff


class FreshnessFilter:
    """Filter component enforcing strict 24-hour freshness with per-source audit logging."""

    def __init__(self, max_age_hours: int = 24):
        self.max_age_hours = max_age_hours

    def filter_records(
        self,
        records: List[Tuple[Any, datetime]],
    ) -> List[Any]:
        """
        Filter records based on publication timestamp.
        `records` is a list of tuples: (record_object_or_dict, parsed_utc_datetime).
        Logs total rejected count per source.
        """
        stats: Dict[str, Dict[str, int]] = {}
        accepted_records = []

        for record, pub_dt in records:
            source_name = "Unknown"
            if hasattr(record, "source") and hasattr(record.source, "name"):
                source_name = record.source.name
            elif isinstance(record, dict) and "source" in record:
                source_name = record["source"].get("name", "Unknown")

            if source_name not in stats:
                stats[source_name] = {"total": 0, "accepted": 0, "rejected": 0}

            stats[source_name]["total"] += 1

            if is_within_freshness_window(pub_dt, max_age_hours=self.max_age_hours):
                accepted_records.append(record)
                stats[source_name]["accepted"] += 1
            else:
                stats[source_name]["rejected"] += 1

        # Audit log summary per source
        for source, count_data in stats.items():
            logger.info(
                "Freshness filter audit summary",
                source=source,
                total_evaluated=count_data["total"],
                accepted_count=count_data["accepted"],
                rejected_stale_count=count_data["rejected"],
                window_hours=self.max_age_hours,
            )

        return accepted_records
