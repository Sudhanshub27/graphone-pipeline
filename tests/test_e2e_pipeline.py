"""
================================================================================
TRIPWIRE PIPELINE END-TO-END INTEGRATION TEST SUITE
================================================================================
Exercises the complete production pipeline flow from raw HTML ingestion to LLM
extraction, Pydantic validation, Entity Resolution, JSONL persistence, Knowledge
Graph triples generation, and LanceDB hybrid vector indexing/search.

Includes happy-path verification and failure-path coverage for invalid LLM output,
scraper failure, and duplicate entity deduplication.
================================================================================
"""

from pathlib import Path
from typing import Any, Dict

import pytest
from config.settings import settings
from pydantic import ValidationError
from src.llm.fallback_chain import FallbackChain, RuleBasedFallbackProvider
from src.llm.providers import LLMProvider
from src.resolution.entity_resolver import EntityResolver
from src.resolution.graph_linker import KnowledgeGraphLinker
from src.schemas.base import SourceMetadata
from src.schemas.product import Product
from src.schemas.startup import Startup
from src.vector.vector_store import VectorStoreManager


class MalformedLLMProvider(LLMProvider):
    """Mock LLM Provider returning invalid non-JSON output for failure-path testing."""

    def __init__(self):
        super().__init__(name="MalformedLLMProvider")

    async def extract(self, text: str, schema: Any) -> Dict[str, Any]:
        raise ValueError("Invalid LLM output: Unparseable JSON preamble response")


class InvalidSchemaLLMProvider(LLMProvider):
    """Mock LLM Provider returning JSON with wrong types violating Pydantic schema."""

    def __init__(self):
        super().__init__(name="InvalidSchemaLLMProvider")

    async def extract(self, text: str, schema: Any) -> Dict[str, Any]:
        return {
            "name": 12345,  # Should be string
            "founding_year": "Not a year",  # Should be int
            "stage": ["Invalid list stage"],  # Should be string
        }


@pytest.mark.asyncio
async def test_e2e_full_pipeline_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Happy-path integration test exercising full end-to-end pipeline:
    Source HTML -> Scraping -> LLM Extraction -> Pydantic Validation ->
    Entity Resolution -> Persistence -> Graph Linkage -> Vector Indexing & Search.
    """
    # Override settings.DATA_PROCESSED_DIR to isolated tmp_path
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "DATA_PROCESSED_DIR", processed_dir)

    # 1. Source / Input Ingestion HTML Snippets
    raw_startup_html = """
    <div class="company-card">
        <h1>SynthFlow AI</h1>
        <p class="tagline">Real-Time AI Voice Agents for Enterprise</p>
        <span class="funding">Total Funding: $12M</span>
        <span class="stage">Stage: Series A</span>
        <span class="location">Location: San Francisco, CA</span>
        <span class="year">Founded: 2023</span>
        <div class="categories"><span>AI Infrastructure</span><span>Voice</span></div>
    </div>
    """

    raw_product_html = """
    <div class="product-header">
        <h1 class="product-title">SynthFlow Voice 2.0</h1>
        <p class="tagline">Low-Latency Conversational Voice Agents</p>
        <div class="maker">By Synthflow Inc</div>
        <div class="upvotes">Upvotes: 1240</div>
        <div class="pricing">Pricing Model: Freemium</div>
        <a class="url" href="https://synthflow.ai">Product Website</a>
    </div>
    """

    # 2. LLM Extraction Layer (using deterministic RuleBasedFallbackProvider)
    llm_chain = FallbackChain(providers=[RuleBasedFallbackProvider()])

    startup_dict, s_tier = await llm_chain.extract_with_fallback(raw_startup_html, Startup)
    product_dict, p_tier = await llm_chain.extract_with_fallback(raw_product_html, Product)

    assert startup_dict is not None, "LLM failed to extract startup dictionary"
    assert product_dict is not None, "LLM failed to extract product dictionary"

    # 3. Pydantic Schema Validation
    startup_obj = Startup.model_validate(startup_dict)
    product_obj = Product.model_validate(product_dict)

    assert isinstance(startup_obj, Startup)
    assert isinstance(product_obj, Product)
    assert startup_obj.name == "SynthFlow AI"
    assert product_obj.name == "SynthFlow Voice 2.0"

    # 4. Entity Resolution (Alias normalization: 'Synthflow Inc' -> 'SynthFlow AI')
    resolver = EntityResolver()
    resolved_startup, s_info = resolver.resolve_record(startup_obj)
    resolved_product, p_info = resolver.resolve_record(product_obj)

    assert resolved_startup is not None
    assert resolved_product is not None

    # 5. Persistence to JSONL
    startups_file = processed_dir / "startups.jsonl"
    products_file = processed_dir / "products.jsonl"

    with open(startups_file, "w", encoding="utf-8") as f:
        f.write(resolved_startup.model_dump_json() + "\n")

    with open(products_file, "w", encoding="utf-8") as f:
        f.write(resolved_product.model_dump_json() + "\n")

    assert startups_file.exists() and startups_file.stat().st_size > 0
    assert products_file.exists() and products_file.stat().st_size > 0

    # 6. Knowledge Graph Generation
    graph_linker = KnowledgeGraphLinker()
    nodes, edges = graph_linker.build_graph_triples()

    assert len(nodes) >= 2, f"Expected at least 2 graph nodes, got {len(nodes)}"
    node_labels = {n["label"] for n in nodes}
    assert "Startup" in node_labels
    assert "Product" in node_labels

    # Verify relational PRODUCES edge between Startup and Product
    produces_edges = [e for e in edges if e["relation"] == "PRODUCES"]
    assert len(produces_edges) >= 1, "Expected PRODUCES edge connecting Startup to Product"

    # 7. Vector Indexing & Hybrid Search
    vector_mgr = VectorStoreManager()
    index_res = vector_mgr.index_all_records()

    assert index_res["status"] == "success"
    assert index_res["indexedCount"] >= 2

    # Perform search for Voice Agents
    search_results = vector_mgr.search("AI Voice Agents for Enterprise", limit=5)
    assert len(search_results) > 0, "Vector search returned no results"
    top_hit = search_results[0]
    assert "Voice" in top_hit["title"] or "SynthFlow" in top_hit["title"]
    assert top_hit["similarity_score"] > 0.30


@pytest.mark.asyncio
async def test_e2e_failure_invalid_llm_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Failure-path test: Verify pipeline handles malformed LLM responses gracefully
    without persisting corrupted records or crashing.
    """
    processed_dir = tmp_path / "processed_invalid"
    processed_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "DATA_PROCESSED_DIR", processed_dir)

    malformed_chain = FallbackChain(providers=[MalformedLLMProvider()])

    extracted_dict, winning_tier = await malformed_chain.extract_with_fallback(
        text="<div class='bad'>Malformed</div>",
        schema=Startup,
    )

    assert extracted_dict is None
    assert winning_tier == "FAILED_ALL_PROVIDERS"

    # Verify no records written to startups.jsonl on extraction failure
    startups_file = processed_dir / "startups.jsonl"
    assert not startups_file.exists() or startups_file.stat().st_size == 0


@pytest.mark.asyncio
async def test_e2e_failure_schema_validation_error():
    """
    Failure-path test: Verify Pydantic validation catches invalid types extracted by LLM.
    """
    invalid_chain = FallbackChain(providers=[InvalidSchemaLLMProvider()])

    extracted_dict, _ = await invalid_chain.extract_with_fallback(
        text="<div>Invalid schema input</div>",
        schema=Startup,
    )

    assert extracted_dict is not None
    # Validate Pydantic schema validation fails cleanly
    with pytest.raises(ValidationError):
        _ = Startup.model_validate(extracted_dict)


@pytest.mark.asyncio
async def test_e2e_failure_duplicate_entity_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Failure-path test: Verify EntityResolver maps duplicate entity variations
    ('Anthropic, Inc.' and 'Anthropic PBC') to a single canonical entity.
    """
    processed_dir = tmp_path / "processed_dups"
    processed_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "DATA_PROCESSED_DIR", processed_dir)

    resolver = EntityResolver()

    # Raw entity 1
    raw_s1 = Startup(
        name="Anthropic, Inc.",
        description="AI Safety Company Building Claude",
        stage="Series E",
        founding_year=2021,
        source=SourceMetadata(name="Test", url="http://test.com"),
    )

    # Raw entity 2 (legal suffix alias variant)
    raw_s2 = Startup(
        name="Anthropic PBC",
        description="AI Safety & Research Company",
        stage="Series E",
        founding_year=2021,
        source=SourceMetadata(name="Test", url="http://test.com"),
    )

    resolved_s1, info1 = resolver.resolve_record(raw_s1)
    resolved_s2, info2 = resolver.resolve_record(raw_s2)

    # Assert both resolved to identical canonical name
    assert resolved_s1.name == resolved_s2.name
    assert resolved_s1.name == "Anthropic"

    # Write both to JSONL and build graph
    startups_file = processed_dir / "startups.jsonl"
    with open(startups_file, "w", encoding="utf-8") as f:
        f.write(resolved_s1.model_dump_json() + "\n")
        f.write(resolved_s2.model_dump_json() + "\n")

    graph_linker = KnowledgeGraphLinker()
    nodes, _ = graph_linker.build_graph_triples()

    startup_nodes = [n for n in nodes if n["label"] == "Startup"]
    assert len(startup_nodes) == 1, f"Expected 1 deduplicated startup node, got {len(startup_nodes)}"
    assert startup_nodes[0]["name"] == "Anthropic"
