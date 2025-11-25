"""Pydantic models for Data Schema v11.

This module defines the data models for candidate profiles based on
the data_schema_v11.yaml configuration.

NOTE: Currently the application uses dict-based profile storage for flexibility
during rapid iteration. These Pydantic models are defined for future use when
we need stricter validation and serialization. The dict approach in the assistant
tools (profile.py) allows for dynamic field additions without schema changes.

TODO: Migrate to these models once the schema is stabilized.
"""

from typing import Any
from datetime import date
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Profile Models (Placeholders - Update with actual schema)
# ============================================================================


class Profile(BaseModel):
    """Main profile model for candidate information."""

    # TODO: Add fields based on data_schema_v11.yaml
    user_id: str
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None

    # Add more fields as schema is defined


class Experience(BaseModel):
    """Work experience model."""

    # TODO: Define complete experience model
    user_id: str
    company: str
    title: str
    start_date: date | None = None
    end_date: date | None = None
    current: bool = False
    description: str | None = None


class Education(BaseModel):
    """Education model."""

    # TODO: Define complete education model
    user_id: str
    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    grade: str | None = None


class Language(BaseModel):
    """Language proficiency model."""

    # TODO: Define complete language model
    user_id: str
    language: str
    proficiency: str  # e.g., "Native", "Fluent", "Intermediate", "Basic"


class ProfileState(BaseModel):
    """
    Complete in-memory view of a user's profile state.

    This aggregates data from multiple tables for easy manipulation
    during the conversation flow.
    """

    # TODO: Expand with all necessary fields
    user_id: str
    profile: Profile | None = None
    experiences: list[Experience] = Field(default_factory=list)
    educations: list[Education] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)

    def is_complete(self) -> bool:
        """
        Check if the profile has all required fields.

        Returns:
            True if profile is complete, False otherwise
        """
        # TODO: Implement based on data_schema_v11.yaml required fields
        if not self.profile:
            return False

        # Check required fields
        required_fields = ["full_name", "email", "phone"]
        for field in required_fields:
            if not getattr(self.profile, field, None):
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert profile state to dictionary."""
        return self.model_dump()
