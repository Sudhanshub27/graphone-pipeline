"""
================================================================================
TRIPWIRE LLM EVALUATION DATASET MODULE
================================================================================

Defines the ExtractionExample data structure and loads manually curated
ground-truth evaluation datasets for LLM extraction benchmarking.
================================================================================
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

DEFAULT_GROUND_TRUTH_PATH = (
    Path(__file__).resolve().parent.parent / "datasets" / "extraction" / "ground_truth.json"
)


@dataclass
class ExtractionExample:
    """Manually curated ground-truth extraction evaluation example."""

    id: str
    target_schema: str  # e.g., 'Startup', 'Product', 'ResearchPaper', 'Job', 'News'
    source_text: str
    expected_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_schema": self.target_schema,
            "source_text": self.source_text,
            "expected_fields": self.expected_fields,
        }


def load_extraction_dataset(dataset_path: Optional[Path] = None) -> List[ExtractionExample]:
    """Load ground-truth extraction dataset from JSON file."""
    path = Path(dataset_path) if dataset_path else DEFAULT_GROUND_TRUTH_PATH
    if not path.exists():
        logger.warning("Ground-truth dataset file missing, attempting fallback locations", path=str(path))
        # Fallback to root datasets/extraction/ground_truth.json if needed
        root_path = Path(__file__).resolve().parent.parent.parent / "datasets" / "extraction" / "ground_truth.json"
        if root_path.exists():
            path = root_path
        else:
            raise FileNotFoundError(f"Ground-truth dataset file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    examples: List[ExtractionExample] = []
    for item in raw_items:
        examples.append(
            ExtractionExample(
                id=item.get("id", f"example-{len(examples)+1}"),
                target_schema=item["target_schema"],
                source_text=item["source_text"],
                expected_fields=item.get("expected_fields", {}),
            )
        )

    logger.info("Loaded extraction evaluation dataset", example_count=len(examples), path=str(path))
    return examples
