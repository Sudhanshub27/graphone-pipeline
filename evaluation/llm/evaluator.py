"""
================================================================================
TRIPWIRE LLM EXTRACTION EVALUATOR MODULE
================================================================================

Executes extraction benchmarking across individual LLM providers and the full
FallbackChain on ground-truth evaluation datasets. Computes accuracy, completeness,
schema validity, missing fields, hallucinations, and extraction latency.

Usage:
  python -m evaluation.llm.evaluator [--provider PROVIDER] [--dataset PATH] [--output PATH]
================================================================================
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

# Ensure project root is in sys.path when executed as module
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import structlog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from evaluation.llm.dataset import ExtractionExample, load_extraction_dataset
from evaluation.llm.metrics import evaluate_example_extraction
from src.llm.fallback_chain import FallbackChain, RuleBasedFallbackProvider
from src.llm.providers import DeepSeekProvider, GeminiProvider, GroqProvider, LLMProvider
from src.schemas.base import BaseRecord
from src.schemas.job import Job
from src.schemas.news import News
from src.schemas.product import Product
from src.schemas.research_paper import ResearchPaper
from src.schemas.startup import Startup

logger = structlog.get_logger(__name__)
console = Console()

SCHEMA_MAP: Dict[str, Type[BaseRecord]] = {
    "Startup": Startup,
    "Product": Product,
    "ResearchPaper": ResearchPaper,
    "Job": Job,
    "News": News,
}


class LLMExtractionEvaluator:
    """Evaluator executing extraction quality benchmarks on individual providers or FallbackChain."""

    def __init__(self, dataset_path: Optional[Path] = None):
        self.dataset = load_extraction_dataset(dataset_path)

    async def evaluate_provider(
        self,
        provider: LLMProvider,
        target_schema_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate a single LLM provider across the evaluation dataset."""
        examples = [
            ex for ex in self.dataset
            if not target_schema_filter or ex.target_schema.lower() == target_schema_filter.lower()
        ]

        if not examples:
            raise ValueError(f"No evaluation examples found for filter '{target_schema_filter}'")

        results: List[Dict[str, Any]] = []
        latencies_ms: List[float] = []

        for ex in examples:
            schema_cls = SCHEMA_MAP.get(ex.target_schema, Startup)
            t0 = time.perf_counter()
            try:
                extracted_dict = await provider.extract(ex.source_text, schema_cls)
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            except Exception as e:
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                extracted_dict = None
                logger.warning("Provider extraction failed during evaluation", provider=provider.name, example_id=ex.id, error=str(e))

            latencies_ms.append(latency_ms)

            eval_res = evaluate_example_extraction(
                extracted_dict=extracted_dict,
                expected_fields=ex.expected_fields,
                schema_cls=schema_cls,
            )
            eval_res["id"] = ex.id
            eval_res["target_schema"] = ex.target_schema
            eval_res["latency_ms"] = latency_ms
            results.append(eval_res)

        return self._build_aggregate_report(
            provider_name=provider.name,
            schema_filter=target_schema_filter or "All Schemas",
            examples=examples,
            results=results,
            latencies_ms=latencies_ms,
            fallback_occurrence_count=0,
        )

    async def evaluate_chain(
        self,
        chain: FallbackChain,
        target_schema_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate the multi-tier FallbackChain across the evaluation dataset."""
        examples = [
            ex for ex in self.dataset
            if not target_schema_filter or ex.target_schema.lower() == target_schema_filter.lower()
        ]

        results: List[Dict[str, Any]] = []
        latencies_ms: List[float] = []
        fallback_count = 0

        for ex in examples:
            schema_cls = SCHEMA_MAP.get(ex.target_schema, Startup)
            t0 = time.perf_counter()
            extracted_dict, winning_provider = await chain.extract_with_fallback(
                text=ex.source_text,
                schema=schema_cls,
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            latencies_ms.append(latency_ms)

            is_fallback = winning_provider != chain.providers[0].name if chain.providers else False
            if is_fallback:
                fallback_count += 1

            eval_res = evaluate_example_extraction(
                extracted_dict=extracted_dict,
                expected_fields=ex.expected_fields,
                schema_cls=schema_cls,
            )
            eval_res["id"] = ex.id
            eval_res["target_schema"] = ex.target_schema
            eval_res["winning_provider"] = winning_provider
            eval_res["latency_ms"] = latency_ms
            results.append(eval_res)

        return self._build_aggregate_report(
            provider_name="FallbackChain",
            schema_filter=target_schema_filter or "All Schemas",
            examples=examples,
            results=results,
            latencies_ms=latencies_ms,
            fallback_occurrence_count=fallback_count,
        )

    def _build_aggregate_report(
        self,
        provider_name: str,
        schema_filter: str,
        examples: List[ExtractionExample],
        results: List[Dict[str, Any]],
        latencies_ms: List[float],
        fallback_occurrence_count: int,
    ) -> Dict[str, Any]:
        """Format structured JSON evaluation report dictionary."""
        total_examples = len(examples)
        schema_valid_count = sum(1 for r in results if r["schema_valid"])
        valid_json_count = sum(1 for r in results if r["is_valid_json"])

        avg_accuracy = round(sum(r["field_accuracy"] for r in results) / total_examples, 4) if total_examples > 0 else 0.0
        avg_completeness = round(sum(r["field_completeness"] for r in results) / total_examples, 4) if total_examples > 0 else 0.0
        avg_latency = round(sum(latencies_ms) / total_examples, 2) if total_examples > 0 else 0.0

        schema_validity_rate = round(schema_valid_count / total_examples, 4) if total_examples > 0 else 0.0
        json_validity_rate = round(valid_json_count / total_examples, 4) if total_examples > 0 else 0.0
        fallback_rate = round(fallback_occurrence_count / total_examples, 4) if total_examples > 0 else 0.0

        all_missing: List[str] = []
        all_unexpected: List[str] = []
        for r in results:
            all_missing.extend(r.get("missing_fields", []))
            all_unexpected.extend(r.get("unexpected_fields", []))

        return {
            "provider": provider_name,
            "schema": schema_filter,
            "examples": total_examples,
            "json_validity": json_validity_rate,
            "schema_validity": schema_validity_rate,
            "field_accuracy": avg_accuracy,
            "field_completeness": avg_completeness,
            "average_latency_ms": avg_latency,
            "fallback_occurrence_rate": fallback_rate,
            "missing_fields": list(set(all_missing)),
            "unexpected_fields": list(set(all_unexpected)),
            "per_example_results": results,
        }


def print_evaluation_summary(report: Dict[str, Any]) -> None:
    """Print Rich terminal summary table of LLM evaluation results."""
    title = f"[bold cyan]LLM EXTRACTION EVALUATION REPORT[/bold cyan] (Provider: [yellow]{report['provider']}[/yellow])"
    console.print("\n")
    console.print(
        Panel(
            f"Target Schema Filter: [bold white]{report['schema']}[/bold white] | Examples Evaluated: [bold white]{report['examples']}[/bold white] | "
            f"Avg Latency: [bold green]{report['average_latency_ms']}ms[/bold green]",
            title=title,
            border_style="cyan",
        )
    )

    table = Table(title="Extraction Quality & Field Metrics", show_header=True, header_style="bold magenta")
    table.add_column("Evaluation Metric", style="cyan", width=28)
    table.add_column("Measured Value / Rate", style="bold green", justify="right")

    table.add_row("1. JSON Validity Rate", f"{round(report['json_validity'] * 100, 2)}%")
    table.add_row("2. Pydantic Schema Validity", f"{round(report['schema_validity'] * 100, 2)}%")
    table.add_row("3. Field-Level Accuracy", f"{round(report['field_accuracy'] * 100, 2)}%")
    table.add_row("4. Field-Level Completeness", f"{round(report['field_completeness'] * 100, 2)}%")
    table.add_row("5. LLM Fallback Occurrence Rate", f"{round(report['fallback_occurrence_rate'] * 100, 2)}%")
    table.add_row("6. Average Extraction Latency", f"{report['average_latency_ms']}ms")

    console.print(table)
    if report["missing_fields"]:
        console.print(f"[yellow]Missing Expected Fields:[/yellow] {', '.join(report['missing_fields'])}")
    if report["unexpected_fields"]:
        console.print(f"[red]Unexpected/Hallucinated Fields:[/red] {', '.join(report['unexpected_fields'])}")
    console.print("\n")


def main():
    """CLI entry point for python -m evaluation.llm.evaluator."""
    parser = argparse.ArgumentParser(
        description="Tripwire LLM Extraction Quality Evaluator Harness"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="chain",
        help="Provider to evaluate: 'rule' (RuleBased), 'gemini', 'groq', 'deepseek', or 'chain' (FallbackChain). Default: chain",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Optional path to custom ground-truth JSON dataset",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation/reports/llm_extraction_eval.json",
        help="Target report JSON destination path",
    )

    args = parser.parse_args()

    evaluator = LLMExtractionEvaluator(dataset_path=Path(args.dataset) if args.dataset else None)

    p_arg = args.provider.lower()
    if p_arg == "rule" or p_arg == "rulebased":
        prov: LLMProvider = RuleBasedFallbackProvider()
        report = asyncio.run(evaluator.evaluate_provider(prov))
    elif p_arg == "gemini":
        prov = GeminiProvider()
        report = asyncio.run(evaluator.evaluate_provider(prov))
    elif p_arg == "groq":
        prov = GroqProvider()
        report = asyncio.run(evaluator.evaluate_provider(prov))
    elif p_arg == "deepseek":
        prov = DeepSeekProvider()
        report = asyncio.run(evaluator.evaluate_provider(prov))
    else:
        # Default: evaluate FallbackChain (with RuleBased provider fallback for resilience)
        chain = FallbackChain(providers=[RuleBasedFallbackProvider()])
        report = asyncio.run(evaluator.evaluate_chain(chain))

    print_evaluation_summary(report)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Saved LLM extraction evaluation report JSON", path=str(out_path))


if __name__ == "__main__":
    main()
