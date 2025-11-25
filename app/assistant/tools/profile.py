"""Profile management tools for the supervisor agent.

These tools allow the agent to read and update user profile data.
"""

import logging
from langchain_core.tools import tool

from app.constants import (
    REQUIRED_PROFILE_FIELDS,
    ALL_PROFILE_FIELDS,
    LIST_FIELDS,
)

logger = logging.getLogger(__name__)


def create_profile_tools(profile_data: dict):
    """
    Create profile tools with access to the profile data.

    Args:
        profile_data: Dictionary containing current profile data (mutable)

    Returns:
        Tuple of tool functions
    """

    @tool
    def get_profile() -> str:
        """
        Get the current user profile data.

        Returns a summary of all profile information collected so far.
        Use this to check what information has been gathered.
        """
        if not profile_data:
            return "No profile data collected yet. Start by asking the user for their information or requesting their CV."

        summary_parts = []
        for field, value in profile_data.items():
            if value is not None:
                if isinstance(value, list):
                    if value:
                        summary_parts.append(f"- {field}: {', '.join(str(v) for v in value[:5])}{'...' if len(value) > 5 else ''}")
                elif isinstance(value, dict):
                    summary_parts.append(f"- {field}: {len(value)} items")
                else:
                    summary_parts.append(f"- {field}: {value}")

        if not summary_parts:
            return "Profile exists but no fields have values yet."

        return "Current profile data:\n" + "\n".join(summary_parts)

    @tool
    def update_profile_field(field: str, value: str) -> str:
        """
        Update a specific field in the user's profile.

        Args:
            field: The profile field to update (e.g., 'name', 'email', 'skills')
            value: The new value for the field

        Returns:
            Confirmation message

        Use this after the user provides information about themselves.
        For skills, pass comma-separated values which will be converted to a list.
        """
        field = field.lower().strip()

        # Convert comma-separated values to list for certain fields
        if field in LIST_FIELDS and isinstance(value, str):
            value = [v.strip() for v in value.split(",") if v.strip()]

        profile_data[field] = value
        logger.info(f"Updated profile field '{field}' to '{value}'")

        # Provide helpful feedback about remaining required fields
        missing_required = [f for f in REQUIRED_PROFILE_FIELDS if not profile_data.get(f)]
        if missing_required:
            return f"✓ Updated {field}. Still need: {', '.join(missing_required)}"
        return f"✓ Updated {field}. Profile looking good!"

    @tool
    def get_missing_fields() -> str:
        """
        Get a list of required fields that are still missing from the profile.

        Returns:
            List of missing required fields and suggestions for what to ask next.

        Use this to determine what information to collect next from the user.
        """
        missing_required = []
        for field in REQUIRED_PROFILE_FIELDS:
            if not profile_data.get(field):
                missing_required.append(field)

        missing_optional = []
        optional_fields = [f for f in ALL_PROFILE_FIELDS if f not in REQUIRED_PROFILE_FIELDS]
        for field in optional_fields:
            if not profile_data.get(field):
                missing_optional.append(field)

        result_parts = []

        if missing_required:
            result_parts.append(f"Missing required fields: {', '.join(missing_required)}")
        else:
            result_parts.append("All required fields are complete!")

        if missing_optional:
            result_parts.append(f"Optional fields to consider: {', '.join(missing_optional[:5])}")

        return "\n".join(result_parts)

    @tool
    def validate_profile() -> str:
        """
        Check if the profile is complete and valid.

        Returns:
            Validation result including completeness status and any issues found.

        Use this to determine if we have enough information to proceed with job matching.
        """
        issues = []

        # Check required fields
        for field in REQUIRED_PROFILE_FIELDS:
            if not profile_data.get(field):
                issues.append(f"Missing required field: {field}")

        # Validate email format if present
        email = profile_data.get("email", "")
        if email and "@" not in email:
            issues.append("Email format appears invalid")

        # Check for minimum useful data
        has_experience = bool(profile_data.get("work_experience") or profile_data.get("current_position"))
        has_skills = bool(profile_data.get("skills"))

        if not has_experience and not has_skills:
            issues.append("Profile needs either work experience or skills for job matching")

        # Calculate completeness
        filled_fields = sum(1 for f in ALL_PROFILE_FIELDS if profile_data.get(f))
        completeness = int((filled_fields / len(ALL_PROFILE_FIELDS)) * 100)

        if issues:
            return f"Almost there! ({completeness}% complete)\n- " + "\n- ".join(issues)
        else:
            return f"Great news! Your profile is {completeness}% complete and ready for matching! 🎉"

    return get_profile, update_profile_field, get_missing_fields, validate_profile
