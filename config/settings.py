import logging
from pathlib import Path
from typing import Optional

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central environment configuration for graphone-pipeline using Pydantic Settings v2.
    Reads from .env file or system environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mock Mode Flag
    MOCK_MODE: bool = Field(
        default=True, description="When true, dashboard API serves realistic mock data"
    )

    # API Keys for LLM Providers & Integrations
    GEMINI_API_KEY: Optional[str] = Field(
        default=None, description="API Key for Google Gemini LLM provider"
    )
    GROQ_API_KEY: Optional[str] = Field(
        default=None, description="API Key for Groq LLM provider"
    )
    DEEPSEEK_API_KEY: Optional[str] = Field(
        default=None, description="API Key for DeepSeek LLM provider"
    )
    GOOGLE_SHEETS_CREDS: Optional[str] = Field(
        default=None,
        description="Path to Google Sheets service account credentials JSON or raw credentials",
    )

    # Scraper, Network, and Concurrency Controls
    MAX_CONCURRENT_SCRAPES: int = Field(
        default=20, description="Maximum number of concurrent scraper worker tasks"
    )
    MAX_CONCURRENT_LLM_CALLS: int = Field(
        default=3, description="Maximum number of parallel LLM extraction calls"
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, description="Global HTTP rate limit per minute per domain"
    )
    HTTP_TIMEOUT_SECONDS: int = Field(
        default=30, description="Default HTTP request timeout in seconds"
    )
    PROXY_LIST: list[str] = Field(
        default_factory=list, description="List of proxy URLs (e.g. ['http://proxy1:8080'])"
    )
    USER_AGENTS: list[str] = Field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        ],
        description="Rotating user agent string pool",
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO", description="Structured log level (DEBUG, INFO, WARNING, ERROR)"
    )

    # Directory Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_RAW_DIR: Path = BASE_DIR / "data" / "raw"
    DATA_PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    LOGS_DIR: Path = BASE_DIR / "logs"

    def setup_directories(self) -> None:
        """Create necessary project data and log directories if missing."""
        self.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)


def configure_logging(log_level: str = "INFO") -> None:
    """Configures structlog for structured JSON logging."""
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


settings = Settings()
