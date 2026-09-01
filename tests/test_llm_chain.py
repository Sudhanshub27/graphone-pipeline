"""
================================================================================
MULTI-TIER LLM EXTRACTION ENGINE TEST SUITE
================================================================================
Executes 5 realistic sample HTML/text snippets through the complete Fallback Chain
(Gemini -> Groq -> DeepSeek -> RuleBased Heuristic).
Prints validated Pydantic schema dictionary outputs + winning provider tier.
================================================================================
"""

import asyncio
from typing import Dict, Any, List
import structlog
import pytest

from src.schemas.startup import Startup
from src.schemas.product import Product
from src.schemas.research_paper import ResearchPaper
from src.schemas.job import Job
from src.schemas.news import News
from src.llm.fallback_chain import FallbackChain

logger = structlog.get_logger(__name__)

# 5 Realistic Sample HTML Snippets
SAMPLE_SNIPPETS: List[Dict[str, Any]] = [
    {
        "name": "Startup Entity Snippet",
        "schema": Startup,
        "html": """
        <div class="company-card">
            <h1>Cogna AI</h1>
            <p class="tagline">Autonomous AI Data Ingestion and Pipeline Infrastructure</p>
            <span class="funding">Total Funding: $18.5M</span>
            <span class="stage">Stage: Series A</span>
            <span class="location">Location: San Francisco, CA</span>
            <span class="year">Founded: 2023</span>
            <span class="team">Employees: 25-50</span>
            <div class="categories"><span>AI Infrastructure</span><span>Developer Tools</span></div>
        </div>
        """,
    },
    {
        "name": "Product Entity Snippet",
        "schema": Product,
        "html": """
        <div class="product-header">
            <h1 class="product-title">SynthFlow Voice 2.0</h1>
            <p class="tagline">Real-Time Low-Latency AI Voice Agents for Enterprise</p>
            <div class="maker">By Synthflow Inc</div>
            <div class="upvotes">Upvotes: 1240</div>
            <div class="pricing">Pricing Model: Freemium ($49/mo)</div>
            <a class="url" href="https://synthflow.ai">Product Website</a>
        </div>
        """,
    },
    {
        "name": "Research Paper Snippet",
        "schema": ResearchPaper,
        "html": """
        <div class="paper-entry">
            <h2>Context-Aware Interleaved Batching for WhisperX</h2>
            <div class="authors">Authors: Carlos Bain, Max Bain</div>
            <div class="abstract">
                While WhisperX accelerates speech transcription via intra-audio batching, it isolates audio segments.
                We propose Context-Aware Interleaved Batching to maintain continuous historical context across batched audio.
            </div>
            <div class="venue">Venue: ArXiv Preprint (cs.CL)</div>
            <a class="pdf" href="https://arxiv.org/pdf/2608.31170v1">Download PDF</a>
            <div class="citations">Citations: 42</div>
        </div>
        """,
    },
    {
        "name": "Job Entity Snippet",
        "schema": Job,
        "html": """
        <div class="job-listing">
            <h1 class="job-title">Senior Distributed Systems Engineer</h1>
            <div class="company">Graphone Tech</div>
            <div class="location">Location: Remote (US / Canada)</div>
            <div class="salary">Salary: $170,000 - $210,000 USD</div>
            <div class="type">Full-time</div>
            <div class="skills">Requirements: Python, Asyncio, FastAPI, Rust, Redis, Kubernetes</div>
        </div>
        """,
    },
    {
        "name": "News Entity Snippet",
        "schema": News,
        "html": """
        <article class="news-post">
            <h1 class="headline">DeepSeek Releases Open-Source V3 Reasoning Model</h1>
            <div class="byline">Published on 2026-08-30 by TechCrunch</div>
            <p class="summary">
                DeepSeek has announced the public release of its flagship open weights model, demonstrating
                unprecedented performance benchmarks in mathematical reasoning and automated software engineering.
            </p>
            <div class="sentiment">Market Sentiment: Bullish (0.92)</div>
        </article>
        """,
    },
]


@pytest.mark.asyncio
async def test_run_llm_fallback_chain_on_sample_snippets():
    """Run 5 sample HTML snippets through the multi-tier LLM fallback chain."""
    chain = FallbackChain()
    results = []

    print("\n" + "=" * 80)
    print("EXECUTING MULTI-TIER LLM EXTRACTION CHAIN ON 5 SAMPLE SNIPPETS")
    print("=" * 80)

    for i, item in enumerate(SAMPLE_SNIPPETS, 1):
        print(f"\n--- Snippet {i}: {item['name']} ({item['schema'].__name__}) ---")
        extracted_dict, winning_tier = await chain.extract_with_fallback(
            text=item["html"],
            schema=item["schema"],
        )

        assert extracted_dict is not None, f"Extraction failed for snippet {i}"
        assert winning_tier != "FAILED_ALL_PROVIDERS", f"All providers failed for snippet {i}"

        print(f"✅ Succeeded Tier: {winning_tier}")
        print("Parsed JSON Output:")
        import json
        print(json.dumps(extracted_dict, indent=2))
        results.append((item['name'], winning_tier, extracted_dict))

    assert len(results) == 5
    print("\n" + "=" * 80)
    print("ALL 5 SNIPPETS SUCCESSFULLY EXTRACTED AND VALIDATED BY PYDANTIC SCHEMAS!")
    print("=" * 80)


def main():
    """Direct execution entry point for standalone CLI testing."""
    asyncio.run(test_run_llm_fallback_chain_on_sample_snippets())


if __name__ == "__main__":
    main()
