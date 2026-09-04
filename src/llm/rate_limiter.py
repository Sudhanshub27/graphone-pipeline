import asyncio
import random
import time
from typing import Any, Callable, Optional, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class ProviderRateLimitError(Exception):
    """Raised when an LLM provider returns HTTP 429 Rate Limit."""

    def __init__(self, provider_name: str, retry_after: Optional[float] = None, message: str = ""):
        self.provider_name = provider_name
        self.retry_after = retry_after
        super().__init__(f"Provider '{provider_name}' rate limit 429 exceeded. {message}")


class LLMRateLimiter:
    """Per-provider token bucket rate limiter to stay within provider API limits."""

    def __init__(self, provider_name: str, requests_per_minute: int = 60):
        self.provider_name = provider_name
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.capacity = float(requests_per_minute)
        self.tokens = float(requests_per_minute)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a token before making an API call, sleeping if depleted."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                logger.info(
                    "LLM Rate limiter throttling",
                    provider=self.provider_name,
                    wait_seconds=round(wait_time, 2),
                )
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


def extract_retry_after(exception: Exception) -> Optional[float]:
    """Extract Retry-After header seconds from provider exception if present."""
    response = getattr(exception, "response", None)
    if response is not None:
        headers = getattr(response, "headers", {})
        retry_after_str = headers.get("retry-after") or headers.get("Retry-After")
        if retry_after_str:
            try:
                return float(retry_after_str)
            except ValueError:
                pass
    return None


async def execute_with_429_retry(
    func: Callable[..., Any],
    provider_name: str,
    max_attempts: int = 2,
    *args,
    **kwargs,
) -> Any:
    """
    Execute LLM call with exponential backoff + full jitter for 429 rate limit responses,
    respecting Retry-After headers when provided.
    Fails fast if daily quota is permanently exhausted.
    """
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            err_str = str(e).lower()

            # Fail fast on daily / project API quota exhaustion (don't retry un-retryable quota limits)
            if "quota exceeded" in err_str or "free_tier_requests" in err_str or "limit: 20" in err_str:
                logger.warning(
                    "Daily API quota exhausted, escalating to fallback chain",
                    provider=provider_name,
                    error=str(e),
                )
                raise ProviderRateLimitError(provider_name, message=str(e)) from e

            status_code = getattr(e, "status_code", None) or getattr(e, "status", None)
            is_429 = status_code == 429 or "429" in err_str or "rate limit" in err_str or "resourceexhausted" in type(e).__name__.lower()

            if not is_429 or attempt == max_attempts:
                raise e

            retry_after = extract_retry_after(e)
            if retry_after is not None:
                sleep_seconds = min(2.0, max(0.5, retry_after))
            else:
                base = 1.5 ** (attempt - 1)
                jitter = random.uniform(0.5, 1.2)
                sleep_seconds = min(2.0, base * jitter)

            logger.warning(
                "429 Rate limit encountered, backing off",
                provider=provider_name,
                attempt=attempt,
                sleep_seconds=round(sleep_seconds, 2),
                error=str(e),
            )
            await asyncio.sleep(sleep_seconds)

    if last_exception:
        raise last_exception
