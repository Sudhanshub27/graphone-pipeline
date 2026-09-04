from typing import List, Literal, Optional

from pydantic import Field

from src.schemas.base import BaseRecord


class Startup(BaseRecord):
    """Pydantic schema representing a Startup company entity."""

    recordType: Literal["startup"] = Field(
        default="startup", description="Entity record discriminator type"
    )
    name: str = Field(..., description="Official name of the startup company")
    description: Optional[str] = Field(
        default=None, description="Brief summary or value proposition of the company"
    )
    website: Optional[str] = Field(
        default=None, description="Official company website landing page URL"
    )
    founding_year: Optional[int] = Field(
        default=None, description="Calendar year the startup was established"
    )
    founders: List[str] = Field(
        default_factory=list, description="List of company founders or key executives"
    )
    stage: Optional[str] = Field(
        default=None,
        description="Current funding/growth stage (e.g., Pre-Seed, Seed, Series A, Growth, Stealth)",
    )
    total_funding: Optional[str] = Field(
        default=None, description="Total venture funding raised (e.g., '$12.5M')"
    )
    location: Optional[str] = Field(
        default=None, description="Headquarters location (City, State, Country)"
    )
    categories_tags: List[str] = Field(
        default_factory=list, description="Industry categories or technology domain tags"
    )
    employee_count: Optional[str] = Field(
        default=None, description="Estimated team size range (e.g., '11-50 employees')"
    )
