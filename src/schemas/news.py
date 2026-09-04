from typing import List, Literal, Optional

from pydantic import Field

from src.schemas.base import BaseRecord


class News(BaseRecord):
    """Pydantic schema representing a News Article or Industry Update entity."""

    recordType: Literal["news"] = Field(
        default="news", description="Entity record discriminator type"
    )
    title: str = Field(..., description="Article headline title")
    summary: Optional[str] = Field(
        default=None, description="Executive summary or lead snippet of the article"
    )
    content: Optional[str] = Field(
        default=None, description="Full body content or raw article text"
    )
    author: Optional[str] = Field(
        default=None, description="Author, reporter, or publishing organization"
    )
    published_at: Optional[str] = Field(
        default=None, description="Article release timestamp or date string"
    )
    categories_tags: List[str] = Field(
        default_factory=list, description="Topic categories, keywords, or section tags"
    )
    sentiment_score: Optional[float] = Field(
        default=None,
        description="Extracted sentiment analysis score ranging from -1.0 (negative) to 1.0 (positive)",
    )
