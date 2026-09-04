from typing import List, Literal, Optional

from pydantic import Field

from src.schemas.base import BaseRecord


class ResearchPaper(BaseRecord):
    """Pydantic schema representing an Academic or Technical Research Paper entity."""

    recordType: Literal["research_paper"] = Field(
        default="research_paper", description="Entity record discriminator type"
    )
    title: str = Field(..., description="Full title of the research paper")
    authors: List[str] = Field(
        default_factory=list, description="List of paper authors and researchers"
    )
    abstract: Optional[str] = Field(
        default=None, description="Executive abstract or paper summary"
    )
    published_date: Optional[str] = Field(
        default=None, description="Date of publication or preprint release"
    )
    pdf_url: Optional[str] = Field(
        default=None, description="Direct URL download link for full PDF paper"
    )
    journal_conference: Optional[str] = Field(
        default=None, description="Publishing journal, arXiv category, or conference venue"
    )
    doi: Optional[str] = Field(
        default=None, description="Digital Object Identifier (DOI)"
    )
    topics: List[str] = Field(
        default_factory=list, description="Research field topics, subjects, or taxonomy tags"
    )
    citations_count: Optional[int] = Field(
        default=0, description="Total recorded citation index count"
    )
