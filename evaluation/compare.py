"""
================================================================================
TRIPWIRE PIPELINE BENCHMARK COMPARISON MODULE
================================================================================

Compares two benchmark JSON reports (baseline vs new) and computes deltas across:
- Throughput (records/sec)
- Cold-start & Steady-state timings
- Latencies (Mean, p50, p95 for Scraper, LLM, Vector Search)
- Rates (Success, Failure, Fallback, Validation, Duplicate Detection)

CLI Usage:
  python -m evaluation.compare baseline.json new.json [--output diff.json]
================================================================================
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import structlog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = structlog.get_logger(__name__)
console = Console()


def calculate_delta(base: float, new: float) -> Tuple[float, float]:
    """Calculate absolute delta (new - base) and percentage change."""
    delta = round(new - base, 4)
    pct_change = round(((new - base) / base) * 100.0, 2) if base != 0 else (100.0 if new > 0 else 0.0)
    return delta, pct_change


def format_change(delta: float, pct: float, higher_is_better: bool = True) -> Tuple[str, str]:
    """Format delta string and styled color code for terminal summary."""
    sign = "+" if delta > 0 else ""
    delta_str = f"{sign}{delta}"
    pct_str = f"{sign}{pct}%"

    if delta == 0:
        style = "white"
    elif (delta > 0 and higher_is_better) or (delta < 0 and not higher_is_better):
        style = "bold green"
    else:
        style = "bold red"

    return f"[{style}]{delta_str}[/{style}]", f"[{style}]{pct_str}[/{style}]"


def compare_reports(
    baseline_path: Path,
    new_path: Path,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compare baseline and new benchmark JSON report files and return comparison dictionary."""
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline report file missing at {baseline_path}")
    if not new_path.exists():
        raise FileNotFoundError(f"New report file missing at {new_path}")

    with open(baseline_path, "r", encoding="utf-8") as f:
        base = json.load(f)

    with open(new_path, "r", encoding="utf-8") as f:
        new = json.load(f)

    # 1. Throughput & Timings
    b_p = base.get("pipeline", {})
    n_p = new.get("pipeline", {})

    tp_delta, tp_pct = calculate_delta(b_p.get("records_per_second", 0), n_p.get("records_per_second", 0))
    cs_delta, cs_pct = calculate_delta(b_p.get("cold_start_time_seconds", 0), n_p.get("cold_start_time_seconds", 0))
    ss_delta, ss_pct = calculate_delta(b_p.get("steady_state_time_seconds", 0), n_p.get("steady_state_time_seconds", 0))

    # 2. Rates
    b_r = base.get("rates", {})
    n_r = new.get("rates", {})

    sr_delta, sr_pct = calculate_delta(b_r.get("success_rate", 0), n_r.get("success_rate", 0))
    fr_delta, fr_pct = calculate_delta(b_r.get("failure_rate", 0), n_r.get("failure_rate", 0))
    fb_delta, fb_pct = calculate_delta(b_r.get("llm_fallback_rate", 0), n_r.get("llm_fallback_rate", 0))
    val_delta, val_pct = calculate_delta(b_r.get("schema_validation_success_rate", 0), n_r.get("schema_validation_success_rate", 0))
    dd_delta, dd_pct = calculate_delta(b_r.get("duplicate_detection_rate", 0), n_r.get("duplicate_detection_rate", 0))

    # 3. Latencies (Scraper, LLM, Vector)
    b_s = base.get("scraper", {}).get("stats_ms", {})
    n_s = new.get("scraper", {}).get("stats_ms", {})
    scr_m_delta, scr_m_pct = calculate_delta(b_s.get("mean", 0), n_s.get("mean", 0))
    scr_p95_delta, scr_p95_pct = calculate_delta(b_s.get("p95", 0), n_s.get("p95", 0))

    b_l = base.get("llm", {}).get("stats_ms", {})
    n_l = new.get("llm", {}).get("stats_ms", {})
    llm_m_delta, llm_m_pct = calculate_delta(b_l.get("mean", 0), n_l.get("mean", 0))
    llm_p95_delta, llm_p95_pct = calculate_delta(b_l.get("p95", 0), n_l.get("p95", 0))

    b_v = base.get("vector_search", {}).get("stats_ms", {})
    n_v = new.get("vector_search", {}).get("stats_ms", {})
    vec_m_delta, vec_m_pct = calculate_delta(b_v.get("mean", 0), n_v.get("mean", 0))
    vec_p95_delta, vec_p95_pct = calculate_delta(b_v.get("p95", 0), n_v.get("p95", 0))

    comparison_dict = {
        "baseline_metadata": base.get("metadata", {}),
        "new_metadata": new.get("metadata", {}),
        "deltas": {
            "throughput_rec_per_sec": {"baseline": b_p.get("records_per_second", 0), "new": n_p.get("records_per_second", 0), "delta": tp_delta, "pct_change": tp_pct},
            "cold_start_seconds": {"baseline": b_p.get("cold_start_time_seconds", 0), "new": n_p.get("cold_start_time_seconds", 0), "delta": cs_delta, "pct_change": cs_pct},
            "steady_state_seconds": {"baseline": b_p.get("steady_state_time_seconds", 0), "new": n_p.get("steady_state_time_seconds", 0), "delta": ss_delta, "pct_change": ss_pct},
            "success_rate": {"baseline": b_r.get("success_rate", 0), "new": n_r.get("success_rate", 0), "delta": sr_delta, "pct_change": sr_pct},
            "failure_rate": {"baseline": b_r.get("failure_rate", 0), "new": n_r.get("failure_rate", 0), "delta": fr_delta, "pct_change": fr_pct},
            "llm_fallback_rate": {"baseline": b_r.get("llm_fallback_rate", 0), "new": n_r.get("llm_fallback_rate", 0), "delta": fb_delta, "pct_change": fb_pct},
            "schema_validation_success_rate": {"baseline": b_r.get("schema_validation_success_rate", 0), "new": n_r.get("schema_validation_success_rate", 0), "delta": val_delta, "pct_change": val_pct},
            "duplicate_detection_rate": {"baseline": b_r.get("duplicate_detection_rate", 0), "new": n_r.get("duplicate_detection_rate", 0), "delta": dd_delta, "pct_change": dd_pct},
            "scraper_latency_mean_ms": {"baseline": b_s.get("mean", 0), "new": n_s.get("mean", 0), "delta": scr_m_delta, "pct_change": scr_m_pct},
            "scraper_latency_p95_ms": {"baseline": b_s.get("p95", 0), "new": n_s.get("p95", 0), "delta": scr_p95_delta, "pct_change": scr_p95_pct},
            "llm_latency_mean_ms": {"baseline": b_l.get("mean", 0), "new": n_l.get("mean", 0), "delta": llm_m_delta, "pct_change": llm_m_pct},
            "llm_latency_p95_ms": {"baseline": b_l.get("p95", 0), "new": n_l.get("p95", 0), "delta": llm_p95_delta, "pct_change": llm_p95_pct},
            "vector_latency_mean_ms": {"baseline": b_v.get("mean", 0), "new": n_v.get("mean", 0), "delta": vec_m_delta, "pct_change": vec_m_pct},
            "vector_latency_p95_ms": {"baseline": b_v.get("p95", 0), "new": n_v.get("p95", 0), "delta": vec_p95_delta, "pct_change": vec_p95_pct},
        },
    }

    # Render Rich comparison summary table
    print_comparison_summary(comparison_dict)

    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(comparison_dict, f, indent=2)
        logger.info("Saved benchmark comparison JSON diff", path=str(out_file))

    return comparison_dict


def print_comparison_summary(comp: Dict[str, Any]) -> None:
    """Print Rich comparison diff summary table."""
    d = comp["deltas"]
    b_meta = comp.get("baseline_metadata", {})
    n_meta = comp.get("new_metadata", {})

    b_commit = b_meta.get("git_commit", "base")
    n_commit = n_meta.get("git_commit", "new")

    title = f"[bold cyan]TRIPWIRE BENCHMARK COMPARISON REPORT[/bold cyan] ([yellow]{b_commit}[/yellow] ➔ [green]{n_commit}[/green])"
    console.print("\n")
    console.print(Panel(f"Baseline Report: [bold white]{b_meta.get('timestamp', 'N/A')}[/bold white]\nNew Report: [bold white]{n_meta.get('timestamp', 'N/A')}[/bold white]", title=title, border_style="cyan"))

    table = Table(title="Benchmark Metric Delta Comparison", show_header=True, header_style="bold magenta")
    table.add_column("Metric Dimension", style="cyan", width=28)
    table.add_column("Baseline", style="white", justify="right")
    table.add_column("New Value", style="bold white", justify="right")
    table.add_column("Delta Change", justify="right")
    table.add_column("% Change", justify="right")

    rows = [
        ("Throughput (rec/sec)", d["throughput_rec_per_sec"], True),
        ("Cold-Start Time (s)", d["cold_start_seconds"], False),
        ("Steady-State Time (s)", d["steady_state_seconds"], False),
        ("Record Success Rate", d["success_rate"], True),
        ("Pipeline Failure Rate", d["failure_rate"], False),
        ("LLM Fallback Rate", d["llm_fallback_rate"], False),
        ("Schema Validation Rate", d["schema_validation_success_rate"], True),
        ("Duplicate Detection Rate", d["duplicate_detection_rate"], True),
        ("Scraper Latency Mean (ms)", d["scraper_latency_mean_ms"], False),
        ("Scraper Latency p95 (ms)", d["scraper_latency_p95_ms"], False),
        ("LLM Latency Mean (ms)", d["llm_latency_mean_ms"], False),
        ("LLM Latency p95 (ms)", d["llm_latency_p95_ms"], False),
        ("Vector Latency Mean (ms)", d["vector_latency_mean_ms"], False),
        ("Vector Latency p95 (ms)", d["vector_latency_p95_ms"], False),
    ]

    for label, metric_data, higher_better in rows:
        b_val = metric_data["baseline"]
        n_val = metric_data["new"]
        delta = metric_data["delta"]
        pct = metric_data["pct_change"]
        d_str, p_str = format_change(delta, pct, higher_is_better=higher_better)
        table.add_row(label, str(b_val), str(n_val), d_str, p_str)

    console.print(table)
    console.print("\n")


def main():
    """CLI entry point for python -m evaluation.compare."""
    parser = argparse.ArgumentParser(
        description="Tripwire Pipeline Benchmark Comparison CLI"
    )
    parser.add_argument(
        "baseline",
        type=str,
        help="Path to baseline benchmark report JSON file",
    )
    parser.add_argument(
        "new",
        type=str,
        help="Path to new benchmark report JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output path to save JSON comparison diff",
    )

    args = parser.parse_args()

    compare_reports(
        baseline_path=Path(args.baseline),
        new_path=Path(args.new),
        output_path=Path(args.output) if args.output else None,
    )


if __name__ == "__main__":
    main()
