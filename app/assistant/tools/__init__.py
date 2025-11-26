"""Tools for the supervisor agent.

This module exports all tools available to the supervisor agent:
- Profile management tools
- Parsing status tools (for async CV parsing)
- Q&A tools

Also provides a unified factory function for creating all tools.
"""

from app.assistant.tools.profile import create_profile_tools
from app.assistant.tools.parsing_status import create_parsing_tools
from app.assistant.tools.qa import get_service_info

__all__ = [
    "create_profile_tools",
    "create_parsing_tools",
    "get_service_info",
    "create_all_tools",
]


def create_all_tools(
    profile_data: dict,
    parsing_results: dict | None = None,
    parsing_in_progress: bool = False,
) -> list:
    """Create all tools for the supervisor agent.

    This unified factory creates all tools with the current state,
    suitable for passing to create_react_agent.

    Args:
        profile_data: Mutable dict containing user profile data
        parsing_results: Results from CV parsing subgraph (or None)
        parsing_in_progress: Whether parsing is currently running

    Returns:
        List of all available tools
    """
    return [
        *create_profile_tools(profile_data),
        *create_parsing_tools(parsing_results, parsing_in_progress),
        get_service_info,
    ]
