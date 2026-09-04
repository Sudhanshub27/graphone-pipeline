import asyncio
import re
import time
from typing import Dict, Optional

import aiohttp
import structlog
from config.settings import settings

logger = structlog.get_logger(__name__)

# Cache for GitHub repository star counts: { "owner/repo": star_count }
_STARS_CACHE: Dict[str, Optional[int]] = {}


def parse_github_repo_owner(github_url: str) -> Optional[tuple[str, str]]:
    """Extract (owner, repo) from various GitHub URL formats."""
    if not github_url:
        return None
    # Matches patterns like github.com/owner/repo or https://github.com/owner/repo/tree/main
    match = re.search(r"github\.com/([^/]+)/([^/\s\?\#]+)", github_url, re.IGNORECASE)
    if match:
        owner = match.group(1)
        repo = match.group(2).rstrip(".git")
        return owner, repo
    return None


async def fetch_github_stars(
    github_url: str,
    session: Optional[aiohttp.ClientSession] = None,
) -> Optional[int]:
    """
    Fetch GitHub star count for a repository using GitHub REST API.
    Handles rate limits using the X-RateLimit-Reset header for precise reset sleep.
    """
    parsed = parse_github_repo_owner(github_url)
    if not parsed:
        return None

    owner, repo = parsed
    cache_key = f"{owner}/{repo}".lower()

    if cache_key in _STARS_CACHE:
        return _STARS_CACHE[cache_key]

    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Graphone-Pipeline/1.0",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    should_close_session = False
    if session is None or session.closed:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        should_close_session = True

    try:
        max_attempts = 3
        for attempt in range(max_attempts):
            async with session.get(api_url, headers=headers) as response:
                # Check rate limiting headers
                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_time_str = response.headers.get("X-RateLimit-Reset")

                if response.status in (403, 429) or (remaining is not None and int(remaining) == 0):
                    if reset_time_str:
                        reset_epoch = float(reset_time_str)
                        current_epoch = time.time()
                        sleep_duration = max(1.0, reset_epoch - current_epoch + 1.0)
                        if sleep_duration > 5.0:
                            logger.warning(
                                "GitHub API rate limit reset duration exceeds max threshold (5s). Skipping star fetch.",
                                url=github_url,
                                reset_at=reset_time_str,
                                sleep_seconds=round(sleep_duration, 1),
                            )
                            _STARS_CACHE[cache_key] = 0
                            return 0

                        logger.warning(
                            "GitHub API rate limit reached. Waiting for reset.",
                            url=github_url,
                            reset_at=reset_time_str,
                            sleep_seconds=round(sleep_duration, 1),
                        )
                        await asyncio.sleep(sleep_duration)
                        continue  # Retry request after reset
                    else:
                        logger.warning("GitHub API 403/429 received without reset header", status=response.status)
                        await asyncio.sleep(2.0 * (attempt + 1))
                        continue

                if response.status == 200:
                    data = await response.json()
                    stars = data.get("stargazers_count", 0)
                    _STARS_CACHE[cache_key] = stars
                    logger.info("Fetched GitHub stars", repo=cache_key, stars=stars)
                    return stars

                if response.status == 404:
                    logger.info("GitHub repository not found", repo=cache_key)
                    _STARS_CACHE[cache_key] = 0
                    return 0

                logger.warning("Unexpected GitHub API response", status=response.status, repo=cache_key)
                return None

    except Exception as e:
        logger.error("Failed to fetch GitHub stars", repo=cache_key, error=str(e))
        return None

    finally:
        if should_close_session and session and not session.closed:
            await session.close()

    return None
