"""
================================================================================
TEST SUITE FOR LLM EXTRACTION EVALUATION FRAMEWORK
================================================================================
Tests field-level scoring, string/numeric/date/list comparison logic, missing field
and hallucination detection, and evaluator report generation.
================================================================================
"""

import pytest

from evaluation.llm.evaluator import LLMExtractionEvaluator
from evaluation.llm.metrics import (
    compare_field_values,
    evaluate_example_extraction,
    extract_numeric_value,
    normalize_date,
    normalize_string,
)
from src.llm.fallback_chain import RuleBasedFallbackProvider
from src.schemas.startup import Startup


def test_normalize_string():
    """Test string normalization helper."""
    assert normalize_string(" OpenAI, Inc. ") == "openai inc"
    assert normalize_string("Anthropic PBC!!!") == "anthropic pbc"
    assert normalize_string("") == ""


def test_extract_numeric_value():
    """Test numeric value extraction from int, float, or string."""
    assert extract_numeric_value(1240) == 1240.0
    assert extract_numeric_value("$18.5M") == 18.5
    assert extract_numeric_value("1,000+") == 1.0
    assert extract_numeric_value("invalid") is None


def test_normalize_date():
    """Test date normalization helper."""
    assert normalize_date("2026-08-30T00:00:00Z") == "2026-08-30"
    assert normalize_date("Founded in 2021") == "2021"


def test_compare_field_values_strings_and_numbers():
    """Test string and numeric field comparison logic."""
    assert compare_field_values("OpenAI, Inc.", "OpenAI Inc") == 1.0
    assert compare_field_values(1240, 1240) == 1.0
    assert compare_field_values("1240", 1240) == 1.0
    assert compare_field_values("Series A", "Series B") == 0.33
    assert compare_field_values("OpenAI", "Anthropic") == 0.0


def test_compare_field_values_lists():
    """Test list set overlap Jaccard similarity comparison."""
    list_a = ["AI Infrastructure", "Developer Tools"]
    list_b = ["Developer Tools", "AI Infrastructure"]
    list_c = ["AI Infrastructure", "Developer Tools", "Cloud"]

    assert compare_field_values(list_a, list_b) == 1.0
    assert compare_field_values(list_a, list_c) == round(2 / 3, 4)


def test_evaluate_example_extraction():
    """Test single example extraction evaluation."""
    expected = {
        "name": "Cogna AI",
        "stage": "Series A",
        "founding_year": 2023,
        "categories_tags": ["AI Infrastructure", "Developer Tools"],
    }

    extracted = {
        "schemaVersion": "1.0.0",
        "recordType": "startup",
        "source": {"name": "HTML", "url": "http://test"},
        "name": "Cogna AI",
        "description": "Autonomous AI Data Ingestion and Pipeline Infrastructure",
        "stage": "Series A",
        "founding_year": 2023,
        "categories_tags": ["AI Infrastructure", "Developer Tools"],
        "unexpected_field_123": "hallucination",
    }

    res = evaluate_example_extraction(
        extracted_dict=extracted,
        expected_fields=expected,
        schema_cls=Startup,
    )

    assert res["is_valid_json"] is True
    assert res["schema_valid"] is True
    assert res["field_accuracy"] == 1.0
    assert res["field_completeness"] == 1.0
    assert res["missing_fields"] == []
    assert "unexpected_field_123" in res["unexpected_fields"]


@pytest.mark.asyncio
async def test_llm_evaluator_with_rule_based_provider():
    """Test LLMExtractionEvaluator running RuleBasedFallbackProvider over ground truth dataset."""
    evaluator = LLMExtractionEvaluator()
    provider = RuleBasedFallbackProvider()

    report = await evaluator.evaluate_provider(provider)

    assert report["provider"] == "RuleBased-Heuristic"
    assert report["examples"] > 0
    assert report["json_validity"] == 1.0
    assert report["schema_validity"] == 1.0
    assert report["field_accuracy"] >= 0.70
    assert report["field_completeness"] >= 0.70
    assert "average_latency_ms" in report
