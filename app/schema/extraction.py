"""Pydantic models for CV extraction with flexible validation.

This module defines schemas for parsing CV data from documents.
The models use ConfigDict(extra="allow") to accept extra fields from
the LLM while still validating the expected structure.

Why flexible validation?
- LLMs may include additional useful fields we didn't anticipate
- Prevents validation failures on minor schema deviations
- Still ensures required fields have correct types
"""

from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class WorkExperience(BaseModel):
    """Work experience entry from CV."""

    model_config = ConfigDict(extra="allow")

    company: str
    title: str
    dates: str | None = None
    highlights: list[str] = Field(default_factory=list)


class Education(BaseModel):
    """Education entry from CV."""

    model_config = ConfigDict(extra="allow")

    institution: str
    degree: str
    field: str | None = None
    dates: str | None = None


class Language(BaseModel):
    """Language proficiency from CV."""

    model_config = ConfigDict(extra="allow")

    language: str
    level: str | None = None


class ExtractedCV(BaseModel):
    """Flexible schema for CV extraction - validates structure but allows extra fields.

    This schema matches the CV_EXTRACTION_PROMPT in prompts.py.
    All fields are optional to handle partial extraction gracefully.
    """

    model_config = ConfigDict(extra="allow")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    current_position: str | None = None
    experience_years: int | float | None = None
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)

    def to_profile_dict(self) -> dict[str, Any]:
        """Convert to profile-compatible dict, filtering None values.

        Returns:
            Dictionary suitable for merging into user profile data.
        """
        data = self.model_dump(exclude_none=True)

        # Ensure nested structures are properly serialized
        if self.work_experience:
            data["work_experience"] = [
                exp.model_dump(exclude_none=True) for exp in self.work_experience
            ]
        if self.education:
            data["education"] = [
                edu.model_dump(exclude_none=True) for edu in self.education
            ]
        if self.languages:
            data["languages"] = [
                lang.model_dump(exclude_none=True) for lang in self.languages
            ]

        return data
