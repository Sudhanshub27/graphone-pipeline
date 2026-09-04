"""
================================================================================
TEST SUITE FOR ENTITY RESOLUTION EVALUATION FRAMEWORK
================================================================================
Tests binary classification metrics (Precision, Recall, F1), method rate calculations,
threshold sweep curves, dataset loading, and evaluator execution.
================================================================================
"""


from evaluation.resolution.evaluator import EntityResolutionEvaluator
from evaluation.resolution.metrics import (
    compute_binary_classification_metrics,
    compute_resolution_evaluation_metrics,
    run_threshold_sweep,
)


def test_compute_binary_classification_metrics():
    """Test precision, recall, F1, and accuracy computation."""
    res = compute_binary_classification_metrics(tp=10, fp=2, fn=3, tn=15)
    assert res["precision"] == round(10 / 12, 4)
    assert res["recall"] == round(10 / 13, 4)
    assert res["accuracy"] == round(25 / 30, 4)
    assert "f1_score" in res


def test_compute_resolution_evaluation_metrics():
    """Test resolution evaluation metrics aggregation."""
    predictions = [
        {"expected_match": True, "predicted_match": True, "method_used": "exact", "confidence_score": 1.0},
        {"expected_match": True, "predicted_match": True, "method_used": "normalized", "confidence_score": 0.95},
        {"expected_match": True, "predicted_match": True, "method_used": "fuzzy", "confidence_score": 0.88},
        {"expected_match": False, "predicted_match": False, "method_used": "unresolved", "confidence_score": 0.30},
        {"expected_match": False, "predicted_match": True, "method_used": "fuzzy", "confidence_score": 0.86},
    ]

    m = compute_resolution_evaluation_metrics(predictions)
    assert m["confusion_matrix"]["true_positives"] == 3
    assert m["confusion_matrix"]["false_positives"] == 1
    assert m["confusion_matrix"]["true_negatives"] == 1
    assert m["confusion_matrix"]["false_negatives"] == 0

    assert m["method_rates"]["exact_match_rate"] == 0.2
    assert m["method_rates"]["normalized_match_rate"] == 0.2
    assert m["method_rates"]["fuzzy_match_rate"] == 0.4
    assert m["method_rates"]["unresolved_rate"] == 0.2


def test_run_threshold_sweep():
    """Test threshold analysis sweep and optimal threshold recommendation."""
    scores = [
        {"expected_match": True, "raw_fuzzy_score": 100.0, "is_exact_or_norm": True},
        {"expected_match": True, "raw_fuzzy_score": 88.0, "is_exact_or_norm": False},
        {"expected_match": True, "raw_fuzzy_score": 82.0, "is_exact_or_norm": False},
        {"expected_match": False, "raw_fuzzy_score": 75.0, "is_exact_or_norm": False},
        {"expected_match": False, "raw_fuzzy_score": 40.0, "is_exact_or_norm": False},
    ]

    sweep = run_threshold_sweep(scores, thresholds=[60.0, 80.0, 90.0])
    assert "threshold_curve" in sweep
    assert len(sweep["threshold_curve"]) == 3
    assert sweep["recommended_threshold"] in (80.0, 90.0, 60.0)


def test_resolution_evaluator_execution():
    """Test EntityResolutionEvaluator executing on ground truth dataset pairs."""
    evaluator = EntityResolutionEvaluator()
    report = evaluator.evaluate(fuzzy_threshold=85.0)

    assert report["total_pairs_evaluated"] > 0
    assert "metrics" in report
    assert "threshold_analysis" in report
    assert "category_breakdown" in report

    cls = report["metrics"]["classification"]
    assert cls["precision"] > 0.0
    assert cls["recall"] > 0.0
    assert cls["f1_score"] > 0.0
