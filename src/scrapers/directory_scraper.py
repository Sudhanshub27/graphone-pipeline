import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from src.scrapers.base import AsyncScraper

logger = structlog.get_logger(__name__)


@dataclass
class DirectoryScraperConfig:
    """Config-driven configuration for directory style scrapers (list -> detail pattern)."""
    name: str
    base_url: str
    listing_url_pattern: str  # e.g., "https://example.com/directory?page={page}"
    start_page: int = 1
    max_pages: int = 3
    item_link_selector: str = "a.item-link"
    next_page_selector: Optional[str] = None
    field_selectors: Dict[str, str] = field(default_factory=dict)
    # Example field_selectors:
    # {
    #     "name": "h1.company-title",
    #     "description": "p.company-desc",
    #     "website": "a.website-link@href",
    #     "categories": "span.tag-badge"
    # }


class DirectoryScraper(AsyncScraper):
    """Generic, config-driven directory scraper for listing + detail page extraction."""

    def __init__(
        self,
        config: DirectoryScraperConfig,
        max_concurrency: Optional[int] = None,
        rate_limit_per_minute: Optional[int] = None,
    ):
        super().__init__(
            max_concurrency=max_concurrency,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        self.config = config

    def parse_field_value(self, soup: BeautifulSoup, raw_selector: str) -> Any:
        """Parse text content or attribute value from BeautifulSoup element based on CSS selector."""
        if "@" in raw_selector:
            css_sel, attr_name = raw_selector.rsplit("@", 1)
        else:
            css_sel, attr_name = raw_selector, None

        elements = soup.select(css_sel)
        if not elements:
            return None

        # If attribute requested (e.g. href)
        if attr_name:
            values = [el.get(attr_name, "").strip() for el in elements if el.has_attr(attr_name)]
            if not values:
                return None
            return values[0] if len(values) == 1 else values

        # Otherwise extract cleaned text
        texts = [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]
        if not texts:
            return None
        return texts[0] if len(texts) == 1 else texts

    async def extract_detail_urls_from_listing(self, page_num: int) -> List[str]:
        """Fetch a single listing page and extract detail URLs using item_link_selector."""
        listing_url = self.config.listing_url_pattern.format(page=page_num)
        logger.info("Scraping listing page", name=self.config.name, page=page_num, url=listing_url)

        try:
            html = await self.fetch(listing_url)
            soup = BeautifulSoup(html, "html.parser")
            elements = soup.select(self.config.item_link_selector)

            detail_urls = []
            for el in elements:
                href = el.get("href")
                if href:
                    full_url = urljoin(self.config.base_url, href)
                    detail_urls.append(full_url)

            # Deduplicate preserving order
            seen = set()
            unique_urls = [u for u in detail_urls if not (u in seen or seen.add(u))]
            logger.info("Found detail URLs", page=page_num, count=len(unique_urls))
            return unique_urls

        except Exception as e:
            logger.error("Failed to scrape listing page", page=page_num, error=str(e))
            return []

    async def scrape_detail_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch detail page and extract structured record dictionary using field_selectors."""
        logger.info("Scraping detail page", url=url)
        try:
            html = await self.fetch(url)
            soup = BeautifulSoup(html, "html.parser")

            extracted_data: Dict[str, Any] = {"detail_url": url}
            for field_name, selector in self.config.field_selectors.items():
                val = self.parse_field_value(soup, selector)
                extracted_data[field_name] = val

            return extracted_data

        except Exception as e:
            logger.error("Failed to scrape detail page", url=url, error=str(e))
            return None

    async def scrape(self) -> List[Dict[str, Any]]:
        """Orchestrate directory pagination and concurrent detail extraction."""
        logger.info("Starting directory scraping pipeline", config_name=self.config.name)

        # Step 1: Collect detail URLs from listing pages
        all_detail_urls: List[str] = []
        for page in range(self.config.start_page, self.config.start_page + self.config.max_pages):
            urls = await self.extract_detail_urls_from_listing(page)
            if not urls:
                logger.info("No more URLs found on listing page, stopping pagination", last_page=page)
                break
            all_detail_urls.extend(urls)

        # Deduplicate all collected detail URLs
        seen = set()
        unique_detail_urls = [u for u in all_detail_urls if not (u in seen or seen.add(u))]
        logger.info("Total unique detail URLs collected", count=len(unique_detail_urls))

        # Step 2: Concurrently fetch detail pages respecting semaphore
        tasks = [self.scrape_detail_page(url) for url in unique_detail_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_records = [r for r in results if isinstance(r, dict) and r is not None]
        logger.info("Completed directory scraping pipeline", total_extracted=len(valid_records))
        return valid_records
