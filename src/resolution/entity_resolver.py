import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog
from config.settings import settings
from pydantic import BaseModel
from rapidfuzz import fuzz

logger = structlog.get_logger(__name__)

SEED_FILE = settings.BASE_DIR / "data" / "seed" / "canonical_startups.json"
MAPPING_LOG_FILE = settings.DATA_PROCESSED_DIR / "entity_mapping_log.jsonl"

# Corporate legal suffix regex pattern
LEGAL_SUFFIXES_REGEX = re.compile(
    r"\b(inc|incorporated|ltd|limited|corp|corporation|llc|co|company|pte|sas|pbc|gmbh|se|bv)\b",
    re.IGNORECASE,
)


def normalize_entity_name(name: str) -> str:
    """
    Normalize entity name for matching:
    - Convert to lowercase
    - Strip corporate legal suffixes (Inc, Ltd, LLC, Corp, etc.)
    - Remove punctuation
    - Collapse whitespace
    """
    if not name:
        return ""
    # Lowercase
    s = name.lower()
    # Strip legal suffixes
    s = LEGAL_SUFFIXES_REGEX.sub("", s)
    # Strip punctuation
    s = re.sub(r"[^\w\s]", "", s)
    # Collapse whitespace
    s = " ".join(s.split())
    return s


class EntityResolver:
    """
    Multi-stage entity resolution engine mapping raw organization names
    to canonical entities using exact, normalized, and fuzzy matching.
    """

    def __init__(
        self,
        seed_file: Optional[Path] = None,
        fuzzy_threshold: float = 85.0,
    ):
        self.seed_file = seed_file or SEED_FILE
        self.fuzzy_threshold = fuzzy_threshold
        self.canonical_entities: List[Dict[str, Any]] = []
        # Fast lookup indexes
        self.exact_map: Dict[str, str] = {}  # lowercase raw alias -> canonical name
        self.norm_map: Dict[str, str] = {}   # normalized alias -> canonical name
        self.all_variants: List[Tuple[str, str]] = []  # [(variant_string, canonical_name)]
        self._load_seed_data()

    def _load_seed_data(self):
        """Load canonical startups and aliases into lookup index tables."""
        if not self.seed_file.exists():
            logger.warning("Seed file missing, initializing empty resolver", path=str(self.seed_file))
            return

        try:
            with open(self.seed_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.canonical_entities = data.get("startups", [])

            for item in self.canonical_entities:
                canonical = item["canonical_name"]
                aliases = item.get("aliases", [canonical])

                # Ensure canonical itself is in aliases
                if canonical not in aliases:
                    aliases.append(canonical)

                for alias in aliases:
                    raw_lower = alias.lower().strip()
                    norm_alias = normalize_entity_name(alias)

                    if raw_lower:
                        self.exact_map[raw_lower] = canonical
                    if norm_alias:
                        self.norm_map[norm_alias] = canonical
                    if norm_alias:
                        self.all_variants.append((norm_alias, canonical))

            logger.info("Loaded canonical entity index", total_canonical=len(self.canonical_entities))

        except Exception as e:
            logger.error("Failed to load canonical startups seed file", error=str(e))

    def log_decision(
        self,
        raw_name: str,
        canonical_name: Optional[str],
        method_used: str,
        confidence_score: float,
    ) -> Dict[str, Any]:
        """Log entity resolution decision to data/processed/entity_mapping_log.jsonl."""
        settings.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        record_id = f"er-{abs(hash(raw_name)) % 10000:04d}"
        status = "merged" if canonical_name else ("needs_review" if confidence_score >= 0.5 else "kept_separate")
        record = {
            "id": record_id,
            "entity_name": canonical_name or raw_name,
            "raw_name": raw_name,
            "canonical_name": canonical_name,
            "entity_type": "startup",
            "method_used": method_used,
            "confidence_score": round(confidence_score, 2),
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            with open(MAPPING_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error("Failed to write to entity_mapping_log.jsonl", error=str(e))

        logger.info(
            "Entity resolution decision",
            raw_name=raw_name,
            canonical=canonical_name,
            method=method_used,
            confidence=record["confidence_score"],
        )
        return record

    def resolve(self, raw_name: str) -> Tuple[Optional[str], str, float]:
        """
        Resolve raw company name against canonical entity dictionary.

        Returns tuple: (canonical_name, method_used, confidence_score)
        Methods:
          - 'exact': exact alias match (confidence 1.0)
          - 'normalized': suffix-stripped/normalized match (confidence 0.95)
          - 'fuzzy': rapidfuzz token_sort_ratio >= threshold (confidence 0.85 - 0.99)
          - 'unresolved': score below threshold (confidence < 0.85, flags for review)
        """
        if not raw_name or not raw_name.strip():
            self.log_decision(raw_name, None, "unresolved", 0.0)
            return None, "unresolved", 0.0

        clean_raw = raw_name.strip()
        raw_lower = clean_raw.lower()

        # Step 1: Exact Match (Fast Path)
        if raw_lower in self.exact_map:
            canonical = self.exact_map[raw_lower]
            self.log_decision(clean_raw, canonical, "exact", 1.0)
            return canonical, "exact", 1.0

        # Step 2: Normalized Match (Legal Suffixes & Punctuation Stripped)
        norm_raw = normalize_entity_name(clean_raw)
        if norm_raw in self.norm_map:
            canonical = self.norm_map[norm_raw]
            self.log_decision(clean_raw, canonical, "normalized", 0.95)
            return canonical, "normalized", 0.95

        # Step 3: Fuzzy Match (RapidFuzz token_sort_ratio)
        best_canonical = None
        best_score = 0.0

        for norm_variant, canonical in self.all_variants:
            score = fuzz.token_sort_ratio(norm_raw, norm_variant)
            if score > best_score:
                best_score = score
                best_canonical = canonical

        confidence = best_score / 100.0

        # Step 4: Evaluate against fuzzy threshold
        if best_score >= self.fuzzy_threshold and best_canonical:
            self.log_decision(clean_raw, best_canonical, "fuzzy", confidence)
            return best_canonical, "fuzzy", confidence

        # Below threshold -> Flag as unresolved ("needs_review")
        self.log_decision(clean_raw, None, "unresolved", confidence)
        return None, "unresolved", confidence

    def resolve_record(self, record: BaseModel) -> Tuple[BaseModel, Dict[str, Any]]:
        """
        Apply entity resolver to a Startup or Product Pydantic schema model object,
        updating entityName / maker_company to canonical form when resolved.
        """
        record_type = getattr(record, "recordType", "")
        raw_target_name = None
        target_field = None

        if record_type == "startup" and hasattr(record, "name"):
            raw_target_name = getattr(record, "name")
            target_field = "name"
        elif record_type == "product" and hasattr(record, "maker_company"):
            raw_target_name = getattr(record, "maker_company")
            target_field = "maker_company"

        if not raw_target_name or not target_field:
            return record, {"method_used": "bypassed", "confidence_score": 1.0}

        canonical, method, conf = self.resolve(raw_target_name)

        if canonical and target_field:
            setattr(record, target_field, canonical)

        decision_info = {
            "raw_name": raw_target_name,
            "canonical_name": canonical,
            "method_used": method,
            "confidence_score": conf,
        }
        return record, decision_info
