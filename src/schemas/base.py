from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceMetadata(BaseModel):
    """Metadata describing the origin of a scraped record."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(
        ...,
        description="Name of the data source provider (e.g., TechCrunch, ProductHunt, ArXiv, LinkedIn)",
    )
    url: str = Field(
        ...,
        description="URL of the web page or API resource from which data was collected",
    )


class BaseRecord(BaseModel):
    """
    Base record containing common fields required across all graphone-pipeline entities:
    - schemaVersion
    - recordType
    - source (SourceMetadata with name and url)
    - collectedAt (ISO 8601 UTC timestamp)
    """

    model_config = ConfigDict(extra="ignore")

    schemaVersion: str = Field(
        default="1.0.0", description="Version of the Pydantic model schema specification"
    )
    recordType: str = Field(
        ..., description="Discriminator type field identifying the entity category"
    )
    source: SourceMetadata = Field(
        ..., description="Source provenance metadata including site name and source URL"
    )
    collectedAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp recorded during ingestion",
    )
