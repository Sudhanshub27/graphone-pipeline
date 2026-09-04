r"""
================================================================================
HORIZONTAL SCALING ARCHITECTURE & DESIGN SPECIFICATION
================================================================================

This scraping framework is architected to scale seamlessly from 500 to 500,000+
records without requiring any internal code modifications. Scaling is achieved
strictly via configuration (adjusting concurrency semaphores, rate limits, and worker counts).

--------------------------------------------------------------------------------
1. LOCAL SCALE-UP (SINGLE-NODE / MULTI-WORKER MODEL)
--------------------------------------------------------------------------------
For single-node workloads (500 to 50,000 records), scaling is handled via Python's
built-in `asyncio.Queue` and non-blocking asynchronous HTTP task pools:

  +-------------------------------------------------------------------------+
  |                           Producer Process                              |
  |  (Discovers URLs from site listings / seed URLs / database queue)       |
  +-------------------------------------------------------------------------+
                                    |
                                    v  (Pushes URLs into Queue)
                         +--------------------+
                         |   asyncio.Queue    |
                         +--------------------+
                           /        |       \  (Popped by N concurrent workers)
                          v         v        v
                   +----------+ +----------+ +----------+
                   | Worker 1 | | Worker 2 | | Worker N |  (AsyncScraper instances)
                   +----------+ +----------+ +----------+
                        |            |            |
                        +------------+------------+
                                     |
                                     v (Semaphore + Token Bucket Control)
                          [ Target HTTP Endpoints ]

- Workers pull target URLs from `asyncio.Queue`.
- Each worker instance enforces:
    * Semaphore-controlled concurrency (e.g., max 20 parallel requests).
    * Per-domain Token Bucket rate-limiting to prevent host overloading.
    * Automatic retries with exponential backoff + jitter via `tenacity`.
    * Rotating User-Agents and Proxy rotation.

--------------------------------------------------------------------------------
2. PRODUCTION SCALE-OUT (MULTI-NODE / DISTRIBUTED MODEL)
--------------------------------------------------------------------------------
For enterprise workloads (50,000 to 500,000+ records), the architecture transitions
from in-memory `asyncio.Queue` to a distributed task message broker:

                             [ Production Upgrade Path ]
  - Task Broker:         Redis / RabbitMQ / Apache Kafka
  - Task Executor:       Celery / ARQ (Async Redis Queue) / Ray / Kubernetes Pods
  - Centralized Storage: PostgreSQL / SQLite (WAL mode) / S3 / Google Sheets

  +-------------------+       +-----------------------+       +---------------------+
  |   Redis Broker    | ----> | Kubernetes Scraper 1  | ----> | Central Storage DB  |
  |  (URL Task Queue) | ----> | Kubernetes Scraper 2  | ----> | (Deduplication Sink)|
  |                   | ----> | Kubernetes Scraper N  | ----> |                     |
  +-------------------+       +-----------------------+       +---------------------+

Because `AsyncScraper` abstracts HTTP fetching, rate limiting, and retries into an
atomic, self-contained worker interface, scaling up horizontally only requires:
  1. Increasing `settings.MAX_CONCURRENT_SCRAPES` in `.env` / environment config.
  2. Spawning additional worker processes or containers.
================================================================================
"""

import abc
import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
import structlog
from config.settings import settings
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

logger = structlog.get_logger(__name__)

# Ensure scrape log file handler exists
SCRAPE_LOG_PATH = settings.LOGS_DIR / "scrape.log"


def setup_scrape_logger() -> logging.Logger:
    """Configure structured file logger dedicated to logs/scrape.log."""
    scrape_logger = logging.getLogger("graphone.scrape")
    scrape_logger.setLevel(logging.INFO)
    if not scrape_logger.handlers:
        fh = logging.FileHandler(SCRAPE_LOG_PATH, encoding="utf-8")
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        fh.setFormatter(formatter)
        scrape_logger.addHandler(fh)
    return scrape_logger


file_logger = setup_scrape_logger()


class TokenBucketRateLimiter:
    """Per-domain Token Bucket rate limiter to prevent hammering host servers."""

    def __init__(self, rate_per_minute: int = 60):
        self.rate = rate_per_minute / 60.0  # tokens per second
        self.capacity = float(rate_per_minute)
        self.tokens: Dict[str, float] = {}
        self.last_update: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, domain: str):
        """Acquire a rate limit token for a specific domain, sleeping if bucket is empty."""
        async with self._lock:
            now = time.monotonic()

            if domain not in self.tokens:
                self.tokens[domain] = self.capacity
                self.last_update[domain] = now

            # Replenish tokens based on elapsed time
            elapsed = now - self.last_update[domain]
            self.tokens[domain] = min(
                self.capacity, self.tokens[domain] + elapsed * self.rate
            )
            self.last_update[domain] = now

            if self.tokens[domain] < 1.0:
                wait_time = (1.0 - self.tokens[domain]) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens[domain] = 0.0
            else:
                self.tokens[domain] -= 1.0


class HTTPStatusRetryableError(Exception):
    """Raised for HTTP 429 (Rate Limited) or 503 (Service Unavailable) to trigger retries."""

    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} retryable error for {url}")


def _is_retryable_exception(exc: BaseException) -> bool:
    """Determine if exception is a transient network issue or 429/503 HTTP status."""
    if isinstance(exc, (aiohttp.ClientError, asyncio.TimeoutError)):
        return True
    if isinstance(exc, HTTPStatusRetryableError):
        return exc.status_code in (429, 503)
    return False


class AsyncScraper(abc.ABC):
    """Abstract Base Scraper providing concurrency control, retries, rate limiting, and logging."""

    def __init__(
        self,
        max_concurrency: Optional[int] = None,
        rate_limit_per_minute: Optional[int] = None,
        proxies: Optional[List[str]] = None,
        user_agents: Optional[List[str]] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.max_concurrency = max_concurrency or settings.MAX_CONCURRENT_SCRAPES
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self.rate_limiter = TokenBucketRateLimiter(
            rate_limit_per_minute or settings.RATE_LIMIT_PER_MINUTE
        )
        self.proxies = proxies or settings.PROXY_LIST
        self.user_agents = user_agents or settings.USER_AGENTS
        self.timeout_seconds = timeout_seconds or settings.HTTP_TIMEOUT_SECONDS
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or initialize the aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def get_random_user_agent(self) -> str:
        """Return a random User-Agent string from the configured pool."""
        if self.user_agents:
            return random.choice(self.user_agents)
        return "Mozilla/5.0 (compatible; GraphoneBot/1.0)"

    def get_random_proxy(self) -> Optional[str]:
        """Return a random proxy URL from config, or None if proxy list is empty."""
        if self.proxies:
            return random.choice(self.proxies)
        return None

    def _log_request(self, url: str, status_code: int, latency_ms: float, error: Optional[str] = None):
        """Write structured log entry to logs/scrape.log."""
        domain = urlparse(url).netloc
        msg = f'"Fetched URL url=\'{url}\' domain=\'{domain}\' status={status_code} latency_ms={latency_ms:.1f}'
        if error:
            msg += f' error=\'{error}\''
        msg += '"'
        file_logger.info(msg)
        logger.info(
            "Scraped URL",
            url=url,
            domain=domain,
            status=status_code,
            latency_ms=round(latency_ms, 1),
            error=error,
        )

    async def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """Fetch URL content with retry logic, rate limiting, and semaphore concurrency control."""
        domain = urlparse(url).netloc

        @retry(
            retry=retry_if_exception(_is_retryable_exception),
            stop=stop_after_attempt(5),
            wait=wait_random_exponential(min=1, max=10),
            reraise=True,
        )
        async def _fetch_with_retry() -> str:
            async with self.semaphore:
                await self.rate_limiter.acquire(domain)
                session = await self.get_session()

                req_headers = {
                    "User-Agent": self.get_random_user_agent(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
                if headers:
                    req_headers.update(headers)

                proxy = self.get_random_proxy()
                start_time = time.monotonic()

                try:
                    async with session.get(url, headers=req_headers, proxy=proxy) as response:
                        latency_ms = (time.monotonic() - start_time) * 1000.0
                        status = response.status

                        if status in (429, 503):
                            self._log_request(url, status, latency_ms, error=f"HTTP {status} retryable")
                            raise HTTPStatusRetryableError(status, url)

                        response.raise_for_status()
                        html = await response.text()
                        self._log_request(url, status, latency_ms)
                        return html

                except Exception as e:
                    latency_ms = (time.monotonic() - start_time) * 1000.0
                    status_code = getattr(e, "status", 0) or getattr(e, "status_code", 0)
                    self._log_request(url, status_code, latency_ms, error=str(e))
                    raise e

        return await _fetch_with_retry()

    @abc.abstractmethod
    async def scrape(self) -> List[Any]:
        """Abstract scrape entry point implemented by concrete scraper subclasses."""
        pass
