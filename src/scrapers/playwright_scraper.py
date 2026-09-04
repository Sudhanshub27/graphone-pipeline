import datetime
from pathlib import Path
from typing import Any, List, Optional
import structlog

from playwright.async_api import async_playwright, Browser, Page, Playwright
from config.settings import settings
from src.scrapers.base import AsyncScraper

logger = structlog.get_logger(__name__)

SCREENSHOTS_DIR = settings.LOGS_DIR / "screenshots"


class PlaywrightScraper(AsyncScraper):
    """Async Playwright scraper equipped with stealth settings and screenshot-on-failure debugging."""

    def __init__(
        self,
        headless: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        max_concurrency: Optional[int] = None,
        rate_limit_per_minute: Optional[int] = None,
    ):
        super().__init__(
            max_concurrency=max_concurrency,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        self.headless = headless
        self.viewport = {"width": viewport_width, "height": viewport_height}
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    async def _init_browser(self):
        """Initialize stealth Playwright Chromium browser instance."""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--ignore-certificate-errors",
            ]
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=launch_args,
            )

    async def close(self):
        """Close browser and stop Playwright process."""
        await super().close()
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def _capture_failure_screenshot(self, page: Page, url: str) -> Path:
        """Capture screenshot on failure for debugging saved to logs/screenshots/."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_url = "".join(c if c.isalnum() else "_" for c in url)[:40]
        filename = f"failure_{timestamp}_{safe_url}.png"
        filepath = SCREENSHOTS_DIR / filename
        try:
            await page.screenshot(path=str(filepath), full_page=True)
            logger.info("Captured failure screenshot", path=str(filepath), url=url)
        except Exception as e:
            logger.error("Failed to capture failure screenshot", error=str(e), url=url)
        return filepath

    async def fetch_page_content(
        self,
        url: str,
        wait_selector: Optional[str] = None,
        timeout_ms: int = 30000,
    ) -> str:
        """Fetch JavaScript-rendered page content with stealth overrides and selector waiting."""
        await self._init_browser()
        assert self.browser is not None

        async with self.semaphore:
            user_agent = self.get_random_user_agent()
            context = await self.browser.new_context(
                viewport=self.viewport,
                user_agent=user_agent,
                locale="en-US",
                timezone_id="America/New_York",
            )

            page = await context.new_page()

            # Apply stealth script: override navigator.webdriver flag
            await page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                """
            )

            try:
                logger.info("Playwright navigating to page", url=url, wait_selector=wait_selector)
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=timeout_ms)

                content = await page.content()
                await context.close()
                return content

            except Exception as e:
                logger.error("Playwright fetch failed", url=url, error=str(e))
                await self._capture_failure_screenshot(page, url)
                await context.close()
                raise e

    async def scrape(self) -> List[Any]:
        """Placeholder for concrete implementation."""
        return []
