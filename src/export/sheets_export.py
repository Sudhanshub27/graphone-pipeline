import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)

# Tab Specifications and Field Ordering
TAB_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "Startups": {
        "file": settings.DATA_PROCESSED_DIR / "startups.jsonl",
        "headers": [
            "schemaVersion",
            "recordType",
            "source_name",
            "source_url",
            "collectedAt",
            "name",
            "description",
            "website",
            "founding_year",
            "founders",
            "stage",
            "total_funding",
            "location",
            "categories_tags",
            "employee_count",
        ],
    },
    "Products": {
        "file": settings.DATA_PROCESSED_DIR / "products.jsonl",
        "headers": [
            "schemaVersion",
            "recordType",
            "source_name",
            "source_url",
            "collectedAt",
            "name",
            "tagline",
            "description",
            "url",
            "maker_company",
            "launch_date",
            "categories_tags",
            "pricing_model",
            "upvotes",
        ],
    },
    "Research Papers": {
        "file": settings.DATA_PROCESSED_DIR / "research_papers.jsonl",
        "headers": [
            "schemaVersion",
            "recordType",
            "source_name",
            "source_url",
            "collectedAt",
            "title",
            "authors",
            "abstract",
            "published_date",
            "pdf_url",
            "journal_conference",
            "doi",
            "topics",
            "citations_count",
        ],
    },
    "Jobs": {
        "file": settings.DATA_PROCESSED_DIR / "jobs.jsonl",
        "headers": [
            "schemaVersion",
            "recordType",
            "source_name",
            "source_url",
            "collectedAt",
            "title",
            "company",
            "location",
            "job_type",
            "salary_range",
            "description",
            "requirements",
            "posted_date",
            "apply_url",
        ],
    },
    "News": {
        "file": settings.DATA_PROCESSED_DIR / "news.jsonl",
        "headers": [
            "schemaVersion",
            "recordType",
            "source_name",
            "source_url",
            "collectedAt",
            "title",
            "summary",
            "content",
            "author",
            "published_at",
            "categories_tags",
            "sentiment_score",
        ],
    },
    "Entity Mapping Log": {
        "file": settings.DATA_PROCESSED_DIR / "entity_mapping_log.jsonl",
        "headers": [
            "raw_name",
            "canonical_name",
            "method_used",
            "confidence_score",
            "timestamp",
        ],
    },
}


def read_jsonl_records(filepath: Path) -> List[Dict[str, Any]]:
    """Read records from line-delimited JSON file."""
    records = []
    if not filepath.exists():
        return records
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    records.append(json.loads(line_str))
    except Exception as e:
        logger.error("Failed to read JSONL file", path=str(filepath), error=str(e))
    return records


def format_cell_value(val: Any) -> str:
    """Format record values (lists, dicts, None) into strings suitable for spreadsheet rows."""
    if val is None:
        return ""
    if isinstance(val, (list, dict)):
        return json.dumps(val)
    return str(val)


def extract_row_values(record: Dict[str, Any], headers: List[str]) -> List[str]:
    """Extract flat row vector from JSON dictionary matching specified header ordering."""
    row = []
    for h in headers:
        if h == "source_name":
            val = record.get("source", {}).get("name", "") if isinstance(record.get("source"), dict) else ""
        elif h == "source_url":
            val = record.get("source", {}).get("url", "") if isinstance(record.get("source"), dict) else ""
        else:
            val = record.get(h)
        row.append(format_cell_value(val))
    return row


class GoogleSheetsExporter:
    """Exporter pushing processed pipeline JSONL outputs to Google Sheets tabs."""

    def __init__(
        self,
        sheet_title: str = "Graphone Pipeline Intelligence Export",
        credentials_file: Optional[str] = None,
    ):
        self.sheet_title = sheet_title
        self.credentials_file = credentials_file or settings.GOOGLE_SHEETS_CREDS

    def export_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Export data from all 6 JSONL outputs into 6 tabs.
        If dry_run or missing credentials, performs local CSV backup export & returns mock URL.
        """
        logger.info("Initiating Google Sheets export", dry_run=dry_run)
        tab_counts = {}

        # 1. Check for gspread & credentials
        has_credentials = (
            not dry_run
            and self.credentials_file
            and Path(self.credentials_file).exists()
        )

        if has_credentials:
            try:
                import gspread

                gc = gspread.service_account(filename=self.credentials_file)

                # Try opening existing spreadsheet or create a new one
                try:
                    sh = gc.open(self.sheet_title)
                except Exception:
                    sh = gc.create(self.sheet_title)
                    # Share publicly for viewing
                    try:
                        sh.share("", perm_type="anyone", role="reader")
                    except Exception:
                        pass

                public_link = f"https://docs.google.com/spreadsheets/d/{sh.id}"

                for tab_name, config in TAB_SCHEMAS.items():
                    records = read_jsonl_records(config["file"])
                    headers = config["headers"]

                    # Format rows
                    rows = [headers] + [extract_row_values(r, headers) for r in records]

                    try:
                        worksheet = sh.worksheet(tab_name)
                    except Exception:
                        worksheet = sh.add_worksheet(title=tab_name, rows=max(len(rows), 100), cols=len(headers))

                    worksheet.clear()
                    worksheet.update(rows)
                    tab_counts[tab_name] = len(records)
                    logger.info("Updated Google Sheets tab", tab=tab_name, rows_written=len(records))

                return {
                    "status": "success",
                    "mode": "live_google_sheets",
                    "sheet_title": self.sheet_title,
                    "public_link": public_link,
                    "tab_counts": tab_counts,
                }

            except Exception as e:
                logger.warning("Google Sheets API export failed, executing local fallback", error=str(e))

        # 2. Local Fallback Export (CSV exports in data/processed/csv_export/)
        csv_dir = settings.DATA_PROCESSED_DIR / "csv_export"
        csv_dir.mkdir(parents=True, exist_ok=True)

        for tab_name, config in TAB_SCHEMAS.items():
            records = read_jsonl_records(config["file"])
            headers = config["headers"]
            tab_counts[tab_name] = len(records)

            csv_file = csv_dir / f"{tab_name.lower().replace(' ', '_')}.csv"
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in records:
                    writer.writerow(extract_row_values(r, headers))

        fallback_link = f"file://{csv_dir}"
        logger.info("Local fallback export completed", csv_dir=str(csv_dir))

        return {
            "status": "success",
            "mode": "dry_run_local_csv" if dry_run else "local_csv_fallback",
            "sheet_title": self.sheet_title,
            "public_link": fallback_link,
            "tab_counts": tab_counts,
        }
