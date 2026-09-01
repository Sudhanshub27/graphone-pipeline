from typing import List, Literal, Optional
from pydantic import Field
from src.schemas.base import BaseRecord


class Job(BaseRecord):
    """Pydantic schema representing a Job Posting / Career Opportunity entity."""

    recordType: Literal["job"] = Field(
        default="job", description="Entity record discriminator type"
    )
    title: str = Field(..., description="Job position title or role name")
    company: str = Field(..., description="Hiring company or organization name")
    location: Optional[str] = Field(
        default=None, description="Office location, country, or Remote status"
    )
    job_type: Optional[str] = Field(
        default=None,
        description="Employment type (e.g., Full-time, Part-time, Contract, Remote, Internship)",
    )
    salary_range: Optional[str] = Field(
        default=None, description="Compensation range or salary package string"
    )
    description: Optional[str] = Field(
        default=None, description="Detailed job description and key responsibilities"
    )
    requirements: List[str] = Field(
        default_factory=list, description="Required technical skills, experience, or qualifications"
    )
    posted_date: Optional[str] = Field(
        default=None, description="Date when job listing was originally published"
    )
    apply_url: Optional[str] = Field(
        default=None, description="URL link for submitting candidate applications"
    )
