r"""
================================================================================
DISTRIBUTED DEDUPLICATION TRACKER ARCHITECTURE
================================================================================

This module maintains persistent tracking of seen URLs and content hashes to
guarantee that re-running scrapers never reprocesses duplicate articles or jobs.

--------------------------------------------------------------------------------
1. LOCAL STANDALONE MODEL (SQLITE STORE)
--------------------------------------------------------------------------------
For single-node ingestion, state is persisted locally in SQLite at
`data/processed/dedup_tracker.db`. The table indexes normalized URL strings and
SHA-256 content fingerprints.

--------------------------------------------------------------------------------
2. DISTRIBUTED PRODUCTION MODEL (REDIS SETS & BLOOM FILTERS)
--------------------------------------------------------------------------------
When scaling to horizontal worker pods across multiple nodes, SQLite is upgraded
to a centralized distributed in-memory cache layer:

  +-----------------------+     SISMEMBER seen:urls <url>     +-------------------+
  | Crawler Worker Pod 1  | --------------------------------> | Redis Cluster /   |
  +-----------------------+ <-------------------------------- | Redis Bloom       |
                                  (0 = unseen, 1 = seen)      +-------------------+
  +-----------------------+                                             ^
  | Crawler Worker Pod N  | --------------------------------------------+
  +-----------------------+             SADD seen:urls <url>

Production Upgrade Interface:
  - Redis Data Structure:  Redis SET (`SADD`, `SISMEMBER`) or `BF.ADD` (Bloom Filter).
  - Time-To-Live (TTL):    Set key TTL to 30 days to bound memory allocation while
                           preventing duplicate crawling.
================================================================================
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Optional
import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)

DB_PATH = settings.DATA_PROCESSED_DIR / "dedup_tracker.db"


class DedupTracker:
    """Persistent SQLite deduplication tracker for cross-run URL and content-hash checking."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        """Create sqlite deduplication table and indexes if missing."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_records (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    content_hash TEXT,
                    source TEXT,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON seen_records(content_hash);")
            conn.commit()

    @staticmethod
    def hash_string(text: str) -> str:
        """Compute SHA-256 hash of string."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def is_seen(self, url: str, content_hash: Optional[str] = None) -> bool:
        """Check if URL or content hash has already been processed."""
        url_key = self.hash_string(url)
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check URL hash match
            cursor.execute("SELECT 1 FROM seen_records WHERE url_hash = ?", (url_key,))
            if cursor.fetchone() is not None:
                return True

            # Check content hash match if provided
            if content_hash:
                c_key = self.hash_string(content_hash)
                cursor.execute("SELECT 1 FROM seen_records WHERE content_hash = ?", (c_key,))
                if cursor.fetchone() is not None:
                    return True

        return False

    def mark_seen(self, url: str, content_hash: Optional[str] = None, source: Optional[str] = None):
        """Record URL and optional content hash as seen."""
        url_key = self.hash_string(url)
        c_key = self.hash_string(content_hash) if content_hash else None
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO seen_records (url_hash, url, content_hash, source)
                    VALUES (?, ?, ?, ?);
                    """,
                    (url_key, url, c_key, source),
                )
                conn.commit()
        except Exception as e:
            logger.error("Failed to mark URL as seen in DedupTracker", url=url, error=str(e))
