from typing import List, Literal, Optional
from pydantic import Field
from src.schemas.base import BaseRecord


class Product(BaseRecord):
    """Pydantic schema representing a Product or Software launch entity."""

    recordType: Literal["product"] = Field(
        default="product", description="Entity record discriminator type"
    )
    name: str = Field(..., description="Name of the product or tool")
    tagline: Optional[str] = Field(
        default=None, description="Short tagline, slogan, or one-line pitch"
    )
    description: Optional[str] = Field(
        default=None, description="Detailed product overview, features, or description"
    )
    url: Optional[str] = Field(
        default=None, description="Direct URL link to the product or store page"
    )
    maker_company: Optional[str] = Field(
        default=None, description="Company, organization, or maker behind the product"
    )
    launch_date: Optional[str] = Field(
        default=None, description="Date when the product was officially launched"
    )
    categories_tags: List[str] = Field(
        default_factory=list, description="Product category tags or tech stack keywords"
    )
    pricing_model: Optional[str] = Field(
        default=None,
        description="Pricing tier (e.g., Free, Freemium, Paid, Open Source, Subscription)",
    )
    upvotes: Optional[int] = Field(
        default=0, description="Total community upvotes, likes, or user rating count"
    )
