"""
================================================================================
TEST SUITE FOR SCIENTIFIC EVALUATION & BENCHMARKING FRAMEWORK
================================================================================
Tests statistical aggregations (mean, median, p50, p95, min, max), rates,
git commit metadata extraction, warm-up handling, multi-iteration execution,
and baseline vs new benchmark comparison.
================================================================================
"""

import json
from pathlib import Path

import pytest
from evaluation.benchmark import run_benchmark
from evaluation.compare import compare_reports
from evaluation.metrics import (
    BenchmarkMetricsCollector,
    calculate_stats,
    get_git_commit,
)


def test_calculate_stats_empty_and_single():
    """Test calculate_stats with empty list and single item."""
    res_empty = calculate_stats([])
    assert res_empty["mean"] == 0.0
    assert res_empty["median"] == 0.0
    assert res_empty["p50"] == 0.0
    assert res_empty["p95"] == 0.0
    assert res_empty["min"] == 0.0
    assert res_empty["max"] == 0.0

    res_single = calculate_stats([42.5])
    assert res_single["mean"] == 42.5
    assert res_single["median"] == 42.5
    assert res_single["min"] == 42.5
    assert res_single["max"] == 42.5


def test_calculate_stats_distribution():
    """Test calculate_stats with numeric range [10..100]."""
    vals = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    res = calculate_stats(vals)
    assert res["mean"] == 55.0
    assert res["median"] == 55.0
    assert res["min"] == 10.0
    assert res["max"] == 100.0
    assert res["p95"] >= 90.0


def test_get_git_commit():
    """Test get_git_commit helper returns a valid string."""
    commit = get_git_commit()
    assert isinstance(commit, str)
    assert len(commit) > 0


def test_benchmark_metrics_collector_rates_and_stats():
    """Test BenchmarkMetricsCollector calculates rates and aggregate stats correctly."""
    collector = BenchmarkMetricsCollector(
        mode="mock",
        requested_records=10,
        iterations=2,
        warmup_records=2,
    )

    collector.record_scrape(latency_ms=10.0, success=True)
    collector.record_scrape(latency_ms=30.0, success=True)

    collector.record_llm_call(provider="RuleBased", latency_ms=5.0, success=True, is_fallback=True)
    collector.record_extraction(success=True, schema_valid=True, missing_fields=0)

    collector.record_resolution("exact")
    collector.record_resolution("normalized")
    collector.record_resolution("fuzzy")
    collector.record_resolution("unresolved")

    collector.record_vector_search(latency_ms=2.0)
    collector.set_vector_indexed_count(10)
    collector.set_timings(cold_start_seconds=0.1, steady_state_seconds=0.4, total_seconds=0.5)

    data = collector.to_dict()

    assert data["metadata"]["git_commit"] == collector.git_commit
    assert data["metadata"]["iterations"] == 2
    assert data["metadata"]["warmup_records"] == 2
    assert data["pipeline"]["cold_start_time_seconds"] == 0.1
    assert data["pipeline"]["steady_state_time_seconds"] == 0.4

    # Rates assertions
    rates = data["rates"]
    assert rates["success_rate"] == 1.0
    assert rates["failure_rate"] == 0.0
    assert rates["llm_fallback_rate"] == 1.0
    assert rates["duplicate_detection_rate"] == 0.75

    # Aggregate stats assertions
    scr_stats = data["scraper"]["stats_ms"]
    assert scr_stats["mean"] == 20.0
    assert scr_stats["min"] == 10.0
    assert scr_stats["max"] == 30.0


@pytest.mark.asyncio
async def test_run_benchmark_mock_iterations(tmp_path: Path):
    """Test multi-iteration benchmark run in mock mode."""
    target_report = tmp_path / "benchmark_scientific_report.json"
    report = await run_benchmark(
        mode="mock",
        record_count=4,
        iterations=2,
        warmup_records=2,
        output_path=target_report,
    )

    assert target_report.exists()
    assert report["metadata"]["mode"] == "mock"
    assert report["metadata"]["iterations"] == 2
    assert report["metadata"]["warmup_records"] == 2
    assert "cold_start_time_seconds" in report["pipeline"]
    assert "steady_state_time_seconds" in report["pipeline"]
    assert "rates" in report
    assert "stats_ms" in report["scraper"]
    assert "stats_ms" in report["llm"]
    assert "stats_ms" in report["vector_search"]


def test_compare_reports_cli(tmp_path: Path):
    """Test comparing baseline vs new benchmark JSON reports."""
    base_file = tmp_path / "baseline.json"
    new_file = tmp_path / "new.json"
    diff_file = tmp_path / "diff.json"

    base_data = {
        "metadata": {"timestamp": "2026-09-04T00:00:00Z", "git_commit": "abc1234"},
        "pipeline": {"records_per_second": 10.0, "cold_start_time_seconds": 0.5, "steady_state_time_seconds": 2.0},
        "rates": {
            "success_rate": 0.90,
            "failure_rate": 0.10,
            "llm_fallback_rate": 0.20,
            "schema_validation_success_rate": 0.90,
            "duplicate_detection_rate": 0.80,
        },
        "scraper": {"stats_ms": {"mean": 20.0, "p95": 30.0}},
        "llm": {"stats_ms": {"mean": 50.0, "p95": 80.0}},
        "vector_search": {"stats_ms": {"mean": 3.0, "p95": 5.0}},
    }

    new_data = {
        "metadata": {"timestamp": "2026-09-04T00:10:00Z", "git_commit": "def5678"},
        "pipeline": {"records_per_second": 15.0, "cold_start_time_seconds": 0.4, "steady_state_time_seconds": 1.5},
        "rates": {
            "success_rate": 0.95,
            "failure_rate": 0.05,
            "llm_fallback_rate": 0.10,
            "schema_validation_success_rate": 0.95,
            "duplicate_detection_rate": 0.85,
        },
        "scraper": {"stats_ms": {"mean": 15.0, "p95": 25.0}},
        "llm": {"stats_ms": {"mean": 40.0, "p95": 60.0}},
        "vector_search": {"stats_ms": {"mean": 2.5, "p95": 4.0}},
    }

    with open(base_file, "w", encoding="utf-8") as f:
        json.dump(base_data, f)
    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(new_data, f)

    comp = compare_reports(base_file, new_file, output_path=diff_file)

    assert diff_file.exists()
    deltas = comp["deltas"]
    assert deltas["throughput_rec_per_sec"]["baseline"] == 10.0
    assert deltas["throughput_rec_per_sec"]["new"] == 15.0
    assert deltas["throughput_rec_per_sec"]["delta"] == 5.0
    assert deltas["throughput_rec_per_sec"]["pct_change"] == 50.0

    assert deltas["success_rate"]["delta"] == 0.05
    assert deltas["llm_fallback_rate"]["delta"] == -0.10
