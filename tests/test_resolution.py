import pytest
from src.resolution.entity_resolver import EntityResolver, normalize_entity_name
from src.schemas.base import SourceMetadata
from src.schemas.product import Product
from src.schemas.startup import Startup


@pytest.fixture
def resolver():
    """Fixture providing initialized EntityResolver instance."""
    return EntityResolver()


def test_normalize_entity_name():
    """Test corporate suffix stripping and punctuation removal."""
    assert normalize_entity_name("OpenAI, Inc.") == "openai"
    assert normalize_entity_name("Anthropic PBC") == "anthropic"
    assert normalize_entity_name("Mistral AI SAS") == "mistral ai"
    assert normalize_entity_name("Scale AI LLC") == "scale ai"


def test_exact_match(resolver):
    """Test exact match against alias list (fast path)."""
    canonical, method, conf = resolver.resolve("openai.com")
    assert canonical == "OpenAI"
    assert method == "exact"
    assert conf == 1.0

    canonical, method, conf = resolver.resolve("Cohere Technologies")
    assert canonical == "Cohere"
    assert method == "exact"
    assert conf == 1.0


def test_normalized_suffix_stripping_match(resolver):
    """Test normalized match after stripping legal suffixes (Inc., LLC, Corp, etc.)."""
    canonical, method, conf = resolver.resolve("Anthropic, Inc.")
    assert canonical == "Anthropic"
    assert method in ("exact", "normalized")
    assert conf >= 0.95

    canonical, method, conf = resolver.resolve("Perplexity AI LLC")
    assert canonical == "Perplexity AI"
    assert method in ("exact", "normalized")
    assert conf >= 0.95


def test_fuzzy_match_above_threshold(resolver):
    """Test fuzzy matching auto-acceptance when rapidfuzz token_sort_ratio >= 85."""
    canonical, method, conf = resolver.resolve("Hugging Face Hub")
    assert canonical == "Hugging Face"
    assert method == "fuzzy"
    assert conf >= 0.85

    canonical_2, method_2, conf_2 = resolver.resolve("Cohere Technologies Cloud")
    assert canonical_2 == "Cohere"
    assert method_2 == "fuzzy"
    assert conf_2 >= 0.85


def test_unresolved_no_match(resolver):
    """Test below threshold / completely unknown entity flags as 'unresolved' (does NOT force match)."""
    canonical, method, conf = resolver.resolve("Totally Unknown Startup X99")
    assert canonical is None
    assert method == "unresolved"
    assert conf < 0.85


def test_resolve_startup_and_product_records(resolver):
    """Test post-extraction resolver updating entity names on Startup and Product schemas."""
    startup = Startup(
        name="OpenAI, Inc.",
        stage="Series A",
        source=SourceMetadata(name="TechCrunch", url="https://techcrunch.com/openai"),
    )
    resolved_startup, info1 = resolver.resolve_record(startup)
    assert resolved_startup.name == "OpenAI"
    assert info1["method_used"] in ("exact", "normalized")

    product = Product(
        name="Claude 3.5 Sonnet",
        tagline="Advanced Reasoning Model",
        maker_company="Anthropic PBC",
        source=SourceMetadata(name="ProductHunt", url="https://producthunt.com/claude"),
    )
    resolved_product, info2 = resolver.resolve_record(product)
    assert resolved_product.maker_company == "Anthropic"
    assert info2["method_used"] in ("exact", "normalized")
