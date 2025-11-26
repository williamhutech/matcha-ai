"""Tools for checking document parsing status.

Simplified for the new LangGraph subgraph pattern. Instead of interacting
with a ParsingStateManager, these tools work with a simple results dict
from the CV parsing subgraph.
"""

import logging
from langchain_core.tools import tool

from app.assistant.cv_parsing_graph import ParsingStatus

logger = logging.getLogger(__name__)


def create_parsing_tools(
    parsing_results: dict | None,
    parsing_in_progress: bool,
):
    """Create tools for checking parsing status.

    Args:
        parsing_results: Results dict from CV parsing subgraph, containing:
            - status: ParsingStatus enum value
            - extracted_data: Dict of extracted profile fields
            - error_message: Error string if failed
            - document_filename: Original filename
        parsing_in_progress: Whether parsing is currently running in background

    Returns:
        Tuple of tool functions
    """

    @tool
    def check_cv_parsing_status() -> str:
        """Check the current status of CV/document parsing.

        Use this to see if:
        - Parsing is in progress (user uploaded a document)
        - Parsing completed successfully (data ready to use)
        - Parsing failed (may need to collect info manually)

        Returns:
            Status summary with next steps.
        """
        if parsing_in_progress:
            return (
                "CV parsing is currently in progress. "
                "Continue the conversation and check again shortly."
            )

        if not parsing_results:
            return "No CV has been uploaded for parsing yet."

        status = parsing_results.get("status")
        filename = parsing_results.get("document_filename", "document")

        if status == ParsingStatus.COMPLETED:
            data = parsing_results.get("extracted_data", {})
            # Count meaningful fields (exclude metadata)
            fields = [
                k for k in data.keys()
                if k not in ["error", "raw_text", "confidence_scores", "missing_fields"]
                and data[k] is not None
            ]
            return (
                f"CV '{filename}' parsed successfully! "
                f"Extracted {len(fields)} fields: {', '.join(fields[:8])}{'...' if len(fields) > 8 else ''}. "
                f"This data has been applied to the profile."
            )

        elif status == ParsingStatus.FAILED:
            error = parsing_results.get("error_message", "Unknown error")
            return (
                f"CV parsing failed for '{filename}': {error}. "
                f"Please collect the user's information through conversation instead."
            )

        return f"Parsing status: {status}"

    @tool
    def is_cv_parsing_in_progress() -> str:
        """Quick check if CV parsing is currently running.

        Use this at the start of each turn to decide whether to
        check parsing status or continue normal conversation.

        Returns:
            'yes' or 'no' with brief context.
        """
        if parsing_in_progress:
            filename = parsing_results.get("document_filename", "document") if parsing_results else "document"
            return f"yes - '{filename}' is being parsed in the background"

        if parsing_results:
            status = parsing_results.get("status")
            filename = parsing_results.get("document_filename", "document")

            if status == ParsingStatus.COMPLETED:
                return f"no - parsing of '{filename}' completed, data has been applied"
            elif status == ParsingStatus.FAILED:
                return f"no - parsing of '{filename}' failed"

        return "no - no active or recent parsing jobs"

    @tool
    def get_parsed_cv_data() -> str:
        """Get a summary of data extracted from the uploaded CV.

        Use this after parsing completes to see what information
        was extracted and is now in the profile.

        Returns:
            Summary of extracted fields or status message.
        """
        if parsing_in_progress:
            return "Parsing still in progress. Check again shortly."

        if not parsing_results:
            return "No CV has been parsed."

        if parsing_results.get("status") != ParsingStatus.COMPLETED:
            return f"Parsing not completed. Status: {parsing_results.get('status')}"

        data = parsing_results.get("extracted_data", {})
        if not data:
            return "Parsing completed but no data was extracted."

        # Build summary
        summary_parts = ["Extracted CV data:"]

        if data.get("name"):
            summary_parts.append(f"- Name: {data['name']}")
        if data.get("email"):
            summary_parts.append(f"- Email: {data['email']}")
        if data.get("phone"):
            summary_parts.append(f"- Phone: {data['phone']}")
        if data.get("location"):
            summary_parts.append(f"- Location: {data['location']}")
        if data.get("current_position"):
            summary_parts.append(f"- Current position: {data['current_position']}")

        if data.get("skills"):
            skills = data["skills"]
            if isinstance(skills, list):
                summary_parts.append(f"- Skills: {len(skills)} found ({', '.join(skills[:5])}{'...' if len(skills) > 5 else ''})")
            else:
                summary_parts.append(f"- Skills: {skills}")

        if data.get("work_experience"):
            exp = data["work_experience"]
            count = len(exp) if isinstance(exp, list) else 1
            summary_parts.append(f"- Work experience: {count} position(s)")

        if data.get("education"):
            edu = data["education"]
            count = len(edu) if isinstance(edu, list) else 1
            summary_parts.append(f"- Education: {count} entry/entries")

        return "\n".join(summary_parts)

    return check_cv_parsing_status, is_cv_parsing_in_progress, get_parsed_cv_data
