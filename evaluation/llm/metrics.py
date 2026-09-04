"""
================================================================================
TRIPWIRE LLM EXTRACTION METRICS & FIELD SCORING MODULE
================================================================================

Implements field-level scoring, string normalization, set overlap for lists,
numeric/date comparisons, Pydantic schema validation checks, missing field detection,
and hallucinated/unexpected field detection.
================================================================================
"""

import math
import re
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError

import structlog

logger = structlog.get_logger(__name__)


def normalize_string(val: str) -> str:
    """Normalize string by lowercasing, stripping punctuation and extra whitespace."""
    if not val:
        return ""
    cleaned = str(val).lower().strip()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_numeric_value(val: Any) -> Optional[float]:
    """Attempt to parse a float value from int, float, or string currency/number format."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        match = re.search(r"[-+]?\d*\.?\d+", val)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


def normalize_date(val: Any) -> str:
    """Extract normalized YYYY-MM-DD or YYYY date representation from string or date object."""
    if not val:
        return ""
    s_val = str(val).strip()
    full_date = re.search(r"(\d{4}-\d{2}-\d{2})", s_val)
    if full_date:
        return full_date.group(1)
    year_match = re.search(r"\b(\d{4})\b", s_val)
    if year_match:
        return year_match.group(1)
    return s_val.lower()


def compare_field_values(actual: Any, expected: Any) -> float:
    """
    Compare actual extracted field value against expected ground-truth field value.
    Returns float score between 0.0 (completely inaccurate/missing) and 1.0 (exact match).
    """
    if expected is None and actual is None:
        return 1.0
    if expected is None or actual is None:
        return 0.0

    # 1. Numeric Comparison
    exp_num = extract_numeric_value(expected)
    act_num = extract_numeric_value(actual)
    if exp_num is not None and act_num is not None and isinstance(expected, (int, float)):
        if math.isclose(exp_num, act_num, rel_tol=0.01, abs_tol=0.01):
            return 1.0
        # Partial score if within 10%
        if exp_num != 0 and abs(exp_num - act_num) / abs(exp_num) <= 0.10:
            return 0.8
        return 0.0

    # 2. List / Set Comparison
    if isinstance(expected, list):
        act_list = actual if isinstance(actual, list) else [actual]
        exp_set = {normalize_string(str(x)) for x in expected if x is not None}
        act_set = {normalize_string(str(x)) for x in act_list if x is not None}

        if not exp_set and not act_set:
            return 1.0
        if not exp_set or not act_set:
            return 0.0

        intersection = exp_set.intersection(act_set)
        union = exp_set.union(act_set)
        return round(len(intersection) / len(union), 4)

    # 3. Date Comparison
    exp_date = normalize_date(expected)
    act_date = normalize_date(actual)
    if exp_date and act_date and len(exp_date) >= 4 and len(act_date) >= 4 and (exp_date.startswith("20") or exp_date.startswith("19")):
        if exp_date == act_date:
            return 1.0
        if exp_date[:4] == act_date[:4]:
            return 0.8

    # 4. String / General Text Comparison
    exp_str = normalize_string(str(expected))
    act_str = normalize_string(str(actual))

    if exp_str == act_str:
        return 1.0

    if not exp_str or not act_str:
        return 0.0

    # Substring / Token Jaccard match
    exp_tokens = set(exp_str.split())
    act_tokens = set(act_str.split())
    if exp_tokens and act_tokens:
        overlap = exp_tokens.intersection(act_tokens)
        union_tokens = exp_tokens.union(act_tokens)
        token_jaccard = len(overlap) / len(union_tokens)

        if token_jaccard >= 0.8:
            return 1.0
        if exp_str in act_str or act_str in exp_str:
            return max(0.85, round(token_jaccard, 2))
        return round(token_jaccard, 2)

    return 0.0


def evaluate_example_extraction(
    extracted_dict: Optional[Dict[str, Any]],
    expected_fields: Dict[str, Any],
    schema_cls: Type[BaseModel],
) -> Dict[str, Any]:
    """
    Evaluate extracted JSON dictionary against ground-truth expected fields and Pydantic schema.
    Computes schema validity, field accuracy, field completeness, missing fields, and hallucinated fields.
    """
    is_valid_json = isinstance(extracted_dict, dict) and len(extracted_dict) > 0
    schema_valid = False

    if is_valid_json:
        try:
            _ = schema_cls.model_validate(extracted_dict)
            schema_valid = True
        except ValidationError:
            schema_valid = False

    field_scores: Dict[str, float] = {}
    missing_fields: List[str] = []
    extracted = extracted_dict or {}

    # Measure expected fields accuracy and completeness
    present_count = 0
    for key, expected_val in expected_fields.items():
        if key in extracted and extracted[key] is not None and extracted[key] != "" and extracted[key] != []:
            present_count += 1
            actual_val = extracted[key]
            score = compare_field_values(actual_val, expected_val)
            field_scores[key] = score
        else:
            missing_fields.append(key)
            field_scores[key] = 0.0

    total_expected = len(expected_fields)
    field_completeness = round(present_count / total_expected, 4) if total_expected > 0 else 0.0
    field_accuracy = round(sum(field_scores.values()) / total_expected, 4) if total_expected > 0 else 0.0

    # Unexpected / Hallucinated fields (extracted keys not in schema or expected)
    schema_field_names = set(schema_cls.model_fields.keys()) if hasattr(schema_cls, "model_fields") else set()
    expected_keys = set(expected_fields.keys())

    unexpected_fields = [
        k for k in extracted.keys()
        if k not in schema_field_names and k not in expected_keys and k not in ("schemaVersion", "recordType", "collectedAt", "source")
    ]

    return {
        "is_valid_json": is_valid_json,
        "schema_valid": schema_valid,
        "field_scores": field_scores,
        "field_accuracy": field_accuracy,
        "field_completeness": field_completeness,
        "missing_fields": missing_fields,
        "unexpected_fields": unexpected_fields,
    }
