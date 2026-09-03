"""
================================================================================
GRAPHONE PIPELINE: ENTERPRISE OBSERVABILITY & PROMETHEUS METRICS MODULE
================================================================================

Provides real-time system metrics, latency histograms, LLM token counters,
entity resolution merger counts, and a Prometheus-formatted /metrics endpoint output.
================================================================================
"""

import time
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Singleton Prometheus & Operational Metrics Collector for Graphone Pipeline."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
            cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self):
        self.records_ingested: Dict[str, int] = {
            "startup": 0,
            "product": 0,
            "research_paper": 0,
            "job": 0,
            "news": 0,
        }
        self.llm_tokens: Dict[str, int] = {
            "Gemini": 0,
            "Groq": 0,
            "DeepSeek": 0,
            "Heuristic": 0,
        }
        self.llm_latency_sum: Dict[str, float] = {
            "Gemini": 0.0,
            "Groq": 0.0,
            "DeepSeek": 0.0,
            "Heuristic": 0.0,
        }
        self.llm_call_count: Dict[str, int] = {
            "Gemini": 0,
            "Groq": 0,
            "DeepSeek": 0,
            "Heuristic": 0,
        }
        self.er_merges: Dict[str, int] = {
            "exact": 0,
            "normalized": 0,
            "fuzzy": 0,
            "unresolved": 0,
        }

    def record_ingested_entity(self, entity_type: str, count: int = 1):
        """Record newly ingested entity count."""
        key = entity_type.lower()
        if key in self.records_ingested:
            self.records_ingested[key] += count
        else:
            self.records_ingested[key] = count

    def record_llm_call(self, provider_family: str, latency_seconds: float, token_count: int):
        """Record LLM call latency and tokens."""
        fam = provider_family.capitalize()
        if fam not in self.llm_tokens:
            fam = "Heuristic"
        self.llm_tokens[fam] += token_count
        self.llm_latency_sum[fam] += latency_seconds
        self.llm_call_count[fam] += 1

    def record_er_merge(self, method: str):
        """Record entity resolution merger method."""
        m = method.lower()
        if m in self.er_merges:
            self.er_merges[m] += 1
        else:
            self.er_merges["unresolved"] += 1

    def generate_prometheus_format(self) -> str:
        """Generate Prometheus exposition text format for /metrics scraping."""
        lines: List[str] = [
            "# HELP graphone_records_ingested_total Total count of processed entity records by type.",
            "# TYPE graphone_records_ingested_total counter",
        ]
        for etype, count in self.records_ingested.items():
            lines.append(f'graphone_records_ingested_total{{entity_type="{etype}"}} {count}')

        lines.extend([
            "# HELP graphone_llm_tokens_total Total tokens processed per LLM provider family.",
            "# TYPE graphone_llm_tokens_total counter",
        ])
        for provider, tokens in self.llm_tokens.items():
            lines.append(f'graphone_llm_tokens_total{{provider="{provider}"}} {tokens}')

        lines.extend([
            "# HELP graphone_llm_calls_total Total LLM calls per provider family.",
            "# TYPE graphone_llm_calls_total counter",
        ])
        for provider, calls in self.llm_call_count.items():
            lines.append(f'graphone_llm_calls_total{{provider="{provider}"}} {calls}')

        lines.extend([
            "# HELP graphone_llm_avg_latency_seconds Average latency per provider call in seconds.",
            "# TYPE graphone_llm_avg_latency_seconds gauge",
        ])
        for provider, ccount in self.llm_call_count.items():
            avg_lat = round(self.llm_latency_sum[provider] / ccount, 4) if ccount > 0 else 0.0
            lines.append(f'graphone_llm_avg_latency_seconds{{provider="{provider}"}} {avg_lat}')

        lines.extend([
            "# HELP graphone_entity_resolution_merges_total Deduplication merges by resolution method.",
            "# TYPE graphone_entity_resolution_merges_total counter",
        ])
        for method, count in self.er_merges.items():
            lines.append(f'graphone_entity_resolution_merges_total{{method="{method}"}} {count}')

        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()
