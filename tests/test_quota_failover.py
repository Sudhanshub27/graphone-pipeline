"""
================================================================================
QUOTA & RATE LIMIT FAILOVER TEST SUITE
================================================================================
Validates that when Tier 1 (Gemini) encounters 429 quota limits or rate limit errors,
the FallbackChain immediately and cleanly cascades to subsequent tiers
(Groq -> DeepSeek -> RuleBased) without raising unhandled exceptions or hanging.
================================================================================
"""

import pytest
from src.llm.fallback_chain import FallbackChain
from src.llm.providers import LLMProvider
from src.schemas.startup import Startup


class QuotaExhaustedMockProvider(LLMProvider):
    """Mock provider simulating HTTP 429 daily quota exhaustion."""

    def __init__(self):
        super().__init__(name="Mock-QuotaExhausted-Gemini", requests_per_minute=60)

    async def extract(self, text: str, schema):
        raise RuntimeError(
            "429 You exceeded your current quota, please check your plan and billing details. "
            "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20"
        )


@pytest.mark.asyncio
async def test_quota_exhaustion_immediate_failover():
    """Verify that quota exhaustion on Tier 1 immediately cascades to RuleBased fallback."""
    failing_provider = QuotaExhaustedMockProvider()
    chain = FallbackChain()
    # Replace provider sequence with failing provider + fallback
    chain.providers = [failing_provider] + chain.providers[1:]

    sample_html = "<h1>Cogna AI</h1><span class='funding'>$18.5M</span>"
    result, provider_used = await chain.extract_with_fallback(sample_html, Startup)

    assert result is not None
    assert provider_used != "Mock-QuotaExhausted-Gemini"
    assert "name" in result
