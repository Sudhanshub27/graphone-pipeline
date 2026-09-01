from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import aiohttp
import httpx
from playwright.async_api import async_playwright
import structlog

logger = structlog.get_logger(__name__)


class BaseScraper(ABC):
    """
    Abstract Base Scraper providing async network fetch capabilities using:
    - aiohttp for high-concurrency static HTTP requests
    - httpx for async REST/JSON endpoints
    - Playwright for client-side JavaScript rendering
    """

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url

    async def fetch_html_aiohttp(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """Fetch raw HTML using aiohttp ClientSession."""
        logger.debug("Fetching raw HTML via aiohttp", url=url)
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()

    async def fetch_json_httpx(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Fetch structured JSON using httpx AsyncClient."""
        logger.debug("Fetching JSON response via httpx", url=url)
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def fetch_rendered_html_playwright(self, url: str) -> str:
        """Render client-side DOM HTML using async Playwright headless browser."""
        logger.debug("Launching Playwright headless session", url=url)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            await browser.close()
            return content

    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """Abstract scrape method to be implemented by site-specific scrapers."""
        pass
