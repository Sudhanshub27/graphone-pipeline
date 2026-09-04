import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.scrapers.base import AsyncScraper, HTTPStatusRetryableError, TokenBucketRateLimiter
from src.scrapers.directory_scraper import DirectoryScraper, DirectoryScraperConfig


class DummyScraper(AsyncScraper):
    """Concrete subclass of AsyncScraper for testing base functionality."""

    async def scrape(self):
        return []


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter():
    """Test token bucket rate limiter bucket refill and throttling logic."""
    limiter = TokenBucketRateLimiter(rate_per_minute=600)  # 10 tokens/sec
    domain = "example.com"

    start_time = asyncio.get_event_loop().time()
    # Consume initial capacity
    for _ in range(5):
        await limiter.acquire(domain)
    end_time = asyncio.get_event_loop().time()

    # Initial bursts should complete almost instantaneously
    assert (end_time - start_time) < 0.2
    assert domain in limiter.tokens


@pytest.mark.asyncio
async def test_async_scraper_retry_on_429():
    """Test AsyncScraper automatic retry on HTTP 429 rate limit response."""
    scraper = DummyScraper(max_concurrency=2)

    # Mock response object
    mock_response = MagicMock()
    mock_response.status = 429
    mock_response.raise_for_status = MagicMock()

    # Context manager mock for session.get()
    cm = AsyncMock()
    cm.__aenter__.return_value = mock_response
    cm.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.get.return_value = cm

    with patch.object(scraper, "get_session", return_value=mock_session):
        with pytest.raises(HTTPStatusRetryableError) as exc_info:
            await scraper.fetch("https://example.com/test-rate-limit")

        assert exc_info.value.status_code == 429
        # Tenacity should attempt up to 5 retries
        assert mock_session.get.call_count == 5

    await scraper.close()


@pytest.mark.asyncio
async def test_directory_scraper_field_extraction():
    """Test DirectoryScraper parsing listing links and detail page CSS selectors."""
    sample_listing_html = """
    <html>
        <body>
            <div class="card"><a class="startup-link" href="/startup/cogna-ai">Cogna AI</a></div>
            <div class="card"><a class="startup-link" href="/startup/synthflow">Synthflow</a></div>
        </body>
    </html>
    """

    sample_detail_html = """
    <html>
        <body>
            <h1 class="title">Cogna AI</h1>
            <p class="description">Autonomous AI Data Pipelines</p>
            <a class="website" href="https://cogna.ai">Website</a>
            <span class="tag">AI</span>
            <span class="tag">Data</span>
        </body>
    </html>
    """

    config = DirectoryScraperConfig(
        name="TestDirectory",
        base_url="https://directory.test",
        listing_url_pattern="https://directory.test/startups?page={page}",
        start_page=1,
        max_pages=1,
        item_link_selector="a.startup-link",
        field_selectors={
            "name": "h1.title",
            "description": "p.description",
            "website": "a.website@href",
            "tags": "span.tag",
        },
    )

    scraper = DirectoryScraper(config=config)

    async def mock_fetch(url: str):
        if "startups?page=1" in url:
            return sample_listing_html
        return sample_detail_html

    with patch.object(scraper, "fetch", side_effect=mock_fetch):
        records = await scraper.scrape()

    assert len(records) == 2
    record = records[0]
    assert record["name"] == "Cogna AI"
    assert record["description"] == "Autonomous AI Data Pipelines"
    assert record["website"] == "https://cogna.ai"
    assert record["tags"] == ["AI", "Data"]

    await scraper.close()
