"""
================================================================================
TRIPWIRE ENTITY RESOLUTION EVALUATION DATASET MODULE
================================================================================

Defines ResolutionPair structure and loads manually labeled entity resolution
evaluation pairs across edge cases (exact, legal suffixes, abbreviations, non-matches).
================================================================================
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

DEFAULT_PAIRS_PATH = (
    Path(__file__).resolve().parent.parent / "datasets" / "resolution" / "pairs.json"
)


@dataclass
class ResolutionPair:
    """Manually labeled entity pair for resolution benchmarking."""

    id: str
    entity_a: str
    entity_b: str
    expected_match: bool
    case_category: str  # e.g., 'exact_duplicates', 'legal_suffixes', 'abbreviations', etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_a": self.entity_a,
            "entity_b": self.entity_b,
            "expected_match": self.expected_match,
            "case_category": self.case_category,
        }


def load_resolution_dataset(dataset_path: Optional[Path] = None) -> List[ResolutionPair]:
    """Load entity resolution pairs dataset from JSON file."""
    path = Path(dataset_path) if dataset_path else DEFAULT_PAIRS_PATH
    if not path.exists():
        logger.warning("Resolution pairs dataset file missing at primary path", path=str(path))
        root_path = Path(__file__).resolve().parent.parent.parent / "datasets" / "resolution" / "pairs.json"
        if root_path.exists():
            path = root_path
        else:
            raise FileNotFoundError(f"Resolution pairs dataset not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    pairs: List[ResolutionPair] = []
    for item in raw_items:
        pairs.append(
            ResolutionPair(
                id=item.get("id", f"er-pair-{len(pairs)+1}"),
                entity_a=item["entity_a"],
                entity_b=item["entity_b"],
                expected_match=bool(item["expected_match"]),
                case_category=item.get("case_category", "general"),
            )
        )

    logger.info("Loaded entity resolution evaluation dataset", pair_count=len(pairs), path=str(path))
    return pairs
