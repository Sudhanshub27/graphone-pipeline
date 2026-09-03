"""
================================================================================
TRIPWIRE ENTITY RESOLUTION METRICS & THRESHOLD ANALYSIS MODULE
================================================================================

Calculates Precision, Recall, F1, Confusion Matrix (TP, FP, FN, TN), Method Rates,
Confidence Distribution, and threshold analysis curves over RapidFuzz thresholds.
================================================================================
"""

from typing import Any, Dict, List, Tuple
from evaluation.metrics import calculate_stats


def compute_binary_classification_metrics(
    tp: int,
    fp: int,
    fn: int,
    tn: int,
) -> Dict[str, float]:
    """Calculate Precision, Recall, F1 Score, and Accuracy from confusion matrix counts."""
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0
    accuracy = round((tp + tn) / (tp + fp + fn + tn), 4) if (tp + fp + fn + tn) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "accuracy": accuracy,
    }


def compute_resolution_evaluation_metrics(
    predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute comprehensive resolution evaluation metrics across predicted entity pairs.
    Each prediction dict contains:
      - expected_match: bool
      - predicted_match: bool
      - method_used: str ('exact', 'normalized', 'fuzzy', 'unresolved')
      - confidence_score: float (0.0 to 1.0)
    """
    tp = fp = fn = tn = 0
    exact_count = norm_count = fuzzy_count = unresolved_count = 0
    confidences: List[float] = []

    for p in predictions:
        exp = p["expected_match"]
        pred = p["predicted_match"]
        conf = p.get("confidence_score", 0.0)
        method = p.get("method_used", "unresolved")

        confidences.append(conf)

        if exp and pred:
            tp += 1
        elif not exp and pred:
            fp += 1
        elif exp and not pred:
            fn += 1
        else:
            tn += 1

        m_clean = method.lower()
        if m_clean == "exact":
            exact_count += 1
        elif m_clean == "normalized":
            norm_count += 1
        elif m_clean == "fuzzy":
            fuzzy_count += 1
        else:
            unresolved_count += 1

    total_pairs = len(predictions)
    cls_metrics = compute_binary_classification_metrics(tp, fp, fn, tn)
    conf_stats = calculate_stats(confidences)

    exact_rate = round(exact_count / total_pairs, 4) if total_pairs > 0 else 0.0
    norm_rate = round(norm_count / total_pairs, 4) if total_pairs > 0 else 0.0
    fuzzy_rate = round(fuzzy_count / total_pairs, 4) if total_pairs > 0 else 0.0

    return {
        "confusion_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "total_pairs": total_pairs,
        },
        "classification": cls_metrics,
        "method_rates": {
            "exact_match_rate": exact_rate,
            "normalized_match_rate": norm_rate,
            "fuzzy_match_rate": fuzzy_rate,
            "unresolved_rate": round(unresolved_count / total_pairs, 4) if total_pairs > 0 else 0.0,
        },
        "confidence_distribution": conf_stats,
    }


def run_threshold_sweep(
    pair_scores: List[Dict[str, Any]],
    thresholds: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Perform threshold analysis sweeping fuzzy matching thresholds (e.g., 50.0 to 95.0).
    Returns metrics table per threshold and recommended threshold based on max F1 score.
    """
    if thresholds is None:
        thresholds = [50.0, 60.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0]

    sweep_results: List[Dict[str, Any]] = []
    best_f1 = -1.0
    recommended_threshold = 85.0

    for thresh in thresholds:
        tp = fp = fn = tn = 0
        for item in pair_scores:
            exp = item["expected_match"]
            # Predict match if exact, normalized, or raw fuzzy score >= threshold
            score_pct = item["raw_fuzzy_score"]
            is_exact_or_norm = item.get("is_exact_or_norm", False)
            pred = is_exact_or_norm or (score_pct >= thresh)

            if exp and pred:
                tp += 1
            elif not exp and pred:
                fp += 1
            elif exp and not pred:
                fn += 1
            else:
                tn += 1

        cls = compute_binary_classification_metrics(tp, fp, fn, tn)
        res_entry = {
            "threshold": thresh,
            "precision": cls["precision"],
            "recall": cls["recall"],
            "f1_score": cls["f1_score"],
            "accuracy": cls["accuracy"],
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }
        sweep_results.append(res_entry)

        if cls["f1_score"] > best_f1:
            best_f1 = cls["f1_score"]
            recommended_threshold = thresh

    return {
        "threshold_curve": sweep_results,
        "recommended_threshold": recommended_threshold,
        "best_f1_score": best_f1,
    }
