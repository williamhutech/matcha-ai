"""Tools for checking document parsing status.

These tools allow the supervisor agent to poll the status of
background parsing operations and apply results to the profile.
"""

import logging
from langchain_core.tools import tool

from app.assistant.parsing_state import ParsingStateManager, ParsingStatus

logger = logging.getLogger(__name__)


def create_parsing_status_tools(
    state_manager: ParsingStateManager,
    profile_data: dict,
):
    """
    Create tools for checking and applying parsing results.

    Args:
        state_manager: The session's parsing state manager
        profile_data: Profile data dict (will be updated when applying results)

    Returns:
        Tuple of tool functions
    """

    @tool
    async def get_parsing_status() -> str:
        """
        Check the current status of document parsing.

        Use this tool to see if a CV/resume is still being parsed,
        has completed, or has failed.

        Returns:
            Status summary of all parsing jobs.
        """
        latest_job = await state_manager.get_latest_job()

        if not latest_job:
            return "No document has been uploaded for parsing."

        status_info = []

        if latest_job.status == ParsingStatus.PENDING:
            status_info.append(
                f"Document '{latest_job.filename}' is queued for parsing."
            )
        elif latest_job.status == ParsingStatus.IN_PROGRESS:
            status_info.append(
                f"Document '{latest_job.filename}' is being parsed... This may take a moment."
            )
        elif latest_job.status == ParsingStatus.RETRYING:
            status_info.append(
                f"Document '{latest_job.filename}' encountered an issue and is being retried (attempt {latest_job.attempt + 1})."
            )
        elif latest_job.status == ParsingStatus.COMPLETED:
            fields_count = (
                len(latest_job.extracted_data) if latest_job.extracted_data else 0
            )
            status_info.append(
                f"Document '{latest_job.filename}' has been parsed successfully! Extracted {fields_count} fields."
            )
            status_info.append(
                "Use apply_parsed_cv_data to add the extracted information to the profile."
            )
        elif latest_job.status == ParsingStatus.FAILED:
            status_info.append(
                f"Document '{latest_job.filename}' could not be parsed: {latest_job.error_message}"
            )
            status_info.append(
                "You may need to ask the user for this information manually."
            )

        return "\n".join(status_info)

    @tool
    async def apply_parsed_cv_data() -> str:
        """
        Apply the extracted CV data to the user's profile.

        Call this after get_parsing_status indicates parsing is complete.
        This will merge the extracted data into the profile.

        Returns:
            Summary of data applied to the profile.
        """
        latest_job = await state_manager.get_latest_job()

        if not latest_job:
            return "No parsed document data available to apply."

        if latest_job.status != ParsingStatus.COMPLETED:
            return f"Cannot apply data - parsing status is '{latest_job.status.value}'. Wait for parsing to complete."

        if not latest_job.extracted_data:
            return "Parsing completed but no data was extracted."

        # Apply extracted data to profile
        extracted = latest_job.extracted_data
        applied_fields = []

        for field, value in extracted.items():
            # Skip metadata fields
            if field in ["confidence_scores", "missing_fields", "error", "raw_text"]:
                continue

            if value is not None:
                profile_data[field] = value
                applied_fields.append(field)

        # Build response
        response_parts = [f"Applied {len(applied_fields)} fields from CV to profile:"]

        if profile_data.get("name"):
            response_parts.append(f"- Name: {profile_data['name']}")
        if profile_data.get("email"):
            response_parts.append(f"- Email: {profile_data['email']}")
        if profile_data.get("phone"):
            response_parts.append(f"- Phone: {profile_data['phone']}")
        if profile_data.get("location"):
            response_parts.append(f"- Location: {profile_data['location']}")
        if profile_data.get("skills"):
            skills = profile_data["skills"]
            count = len(skills) if isinstance(skills, list) else 1
            response_parts.append(f"- Skills: {count} found")
        if profile_data.get("work_experience"):
            exp = profile_data["work_experience"]
            count = len(exp) if isinstance(exp, list) else 1
            response_parts.append(f"- Work experience: {count} positions")
        if profile_data.get("education"):
            edu = profile_data["education"]
            count = len(edu) if isinstance(edu, list) else 1
            response_parts.append(f"- Education: {count} entries")

        # Note missing fields
        missing = extracted.get("missing_fields", [])
        if missing:
            response_parts.append(f"\nFields not found in CV: {', '.join(missing)}")
            response_parts.append("Consider asking the user for this information.")

        logger.info(f"Applied parsed CV data: {applied_fields}")
        return "\n".join(response_parts)

    @tool
    async def is_cv_parsing_in_progress() -> str:
        """
        Quick check if CV parsing is currently running.

        Use this at the start of each turn to see if you should
        check parsing status or continue the conversation.

        Returns:
            'yes' if parsing is in progress, 'no' otherwise, plus brief context.
        """
        active_jobs = await state_manager.get_active_jobs()

        if active_jobs:
            job = active_jobs[0]
            return f"yes - '{job.filename}' is being parsed (status: {job.status.value})"

        # Check for completed but unapplied jobs
        latest = await state_manager.get_latest_job()
        if latest and latest.status == ParsingStatus.COMPLETED and latest.extracted_data:
            return f"no - but '{latest.filename}' parsing completed and is ready to apply"
        elif latest and latest.status == ParsingStatus.FAILED:
            return f"no - '{latest.filename}' parsing failed: {latest.error_message}"

        return "no - no active parsing jobs"

    return get_parsing_status, apply_parsed_cv_data, is_cv_parsing_in_progress
