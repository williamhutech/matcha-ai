"""CV Parsing as LangGraph Subgraph.

This module implements CV document parsing as a LangGraph workflow,
providing better observability (via LangSmith traces), cleaner retry logic
via state machine patterns, and a reusable graph component.

The graph handles:
- Document parsing with the existing parse_cv_from_bytes function
- Automatic retries for transient errors (rate limits, timeouts)
- State tracking for parsing progress
"""

import asyncio
import logging
from typing import TypedDict, Any
from enum import Enum

from langgraph.graph import StateGraph, START, END

from app.documents.parsing import parse_cv_from_bytes
from app.constants import DEFAULT_MAX_RETRIES, RETRY_BACKOFF_SECONDS

logger = logging.getLogger(__name__)


class ParsingStatus(str, Enum):
    """Status states for CV parsing workflow."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class CVParsingState(TypedDict):
    """State schema for the CV parsing subgraph.

    Attributes:
        document_content: Raw bytes of the uploaded document
        document_filename: Original filename for logging/display
        document_mime: MIME type (e.g., 'application/pdf')
        status: Current parsing status
        attempt: Current attempt number (for retry tracking)
        max_retries: Maximum number of retry attempts
        error_message: Error message if parsing failed
        extracted_data: Extracted CV data on success
    """

    document_content: bytes
    document_filename: str
    document_mime: str
    status: ParsingStatus
    attempt: int
    max_retries: int
    error_message: str | None
    extracted_data: dict[str, Any] | None


# Patterns that indicate transient (retryable) errors
TRANSIENT_ERROR_PATTERNS = ("timeout", "rate_limit", "connection", "503", "429", "502", "504")


def should_retry(state: CVParsingState) -> str:
    """Determine next step based on parsing result.

    Returns:
        'complete' - Parsing succeeded
        'failed' - Parsing failed permanently
        'retry' - Should retry (transient error)
    """
    if state["status"] == ParsingStatus.COMPLETED:
        return "complete"

    # Check if we can retry
    if state["attempt"] < state["max_retries"]:
        error = state.get("error_message", "") or ""
        # Only retry transient errors
        if any(pattern in error.lower() for pattern in TRANSIENT_ERROR_PATTERNS):
            logger.info(f"Transient error detected, will retry: {error[:100]}")
            return "retry"

    return "failed"


async def parse_document(state: CVParsingState) -> dict[str, Any]:
    """Execute document parsing node.

    Calls the existing parse_cv_from_bytes function and updates state
    based on the result.
    """
    attempt = state["attempt"] + 1
    filename = state["document_filename"]

    logger.info(f"Parsing document '{filename}', attempt {attempt}/{state['max_retries']}")

    try:
        extracted = await parse_cv_from_bytes(
            content=state["document_content"],
            mime_type=state["document_mime"],
            filename=filename,
        )

        # Check for error in result (parse_cv_from_bytes returns {"error": ...} on failure)
        if "error" in extracted:
            logger.warning(f"Parsing returned error: {extracted['error']}")
            return {
                "status": ParsingStatus.FAILED,
                "attempt": attempt,
                "error_message": extracted["error"],
                "extracted_data": None,
            }

        # Success
        logger.info(f"Successfully parsed '{filename}': {len(extracted)} fields extracted")
        return {
            "status": ParsingStatus.COMPLETED,
            "attempt": attempt,
            "extracted_data": extracted,
            "error_message": None,
        }

    except Exception as e:
        logger.warning(f"Parsing exception on attempt {attempt}: {e}")
        return {
            "status": ParsingStatus.FAILED,
            "attempt": attempt,
            "error_message": str(e),
            "extracted_data": None,
        }


async def wait_before_retry(state: CVParsingState) -> dict[str, Any]:
    """Wait before retrying with exponential backoff.

    Uses RETRY_BACKOFF_SECONDS from constants for backoff timing.
    """
    attempt_idx = state["attempt"] - 1
    backoff_idx = min(attempt_idx, len(RETRY_BACKOFF_SECONDS) - 1)
    backoff = RETRY_BACKOFF_SECONDS[backoff_idx]

    logger.info(f"Waiting {backoff}s before retry attempt {state['attempt'] + 1}")
    await asyncio.sleep(backoff)

    # Return empty dict - no state changes needed
    return {}


def build_cv_parsing_graph() -> StateGraph:
    """Build and compile the CV parsing subgraph.

    Graph structure:
        START -> parse -> [complete] -> END
                      -> [failed]   -> END
                      -> [retry]    -> wait_retry -> parse

    Returns:
        Compiled StateGraph ready for invocation
    """
    builder = StateGraph(CVParsingState)

    # Add nodes
    builder.add_node("parse", parse_document)
    builder.add_node("wait_retry", wait_before_retry)

    # Add edges
    builder.add_edge(START, "parse")
    builder.add_conditional_edges(
        "parse",
        should_retry,
        {
            "complete": END,
            "failed": END,
            "retry": "wait_retry",
        },
    )
    builder.add_edge("wait_retry", "parse")

    return builder.compile()


# Singleton compiled graph instance
cv_parsing_graph = build_cv_parsing_graph()


async def invoke_cv_parsing(
    content: bytes,
    filename: str,
    mime_type: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> CVParsingState:
    """Convenience function to invoke the CV parsing graph.

    Args:
        content: Document bytes
        filename: Original filename
        mime_type: MIME type of document
        max_retries: Maximum retry attempts (default from constants)

    Returns:
        Final CVParsingState with results
    """
    initial_state: CVParsingState = {
        "document_content": content,
        "document_filename": filename,
        "document_mime": mime_type,
        "status": ParsingStatus.PENDING,
        "attempt": 0,
        "max_retries": max_retries,
        "error_message": None,
        "extracted_data": None,
    }

    result = await cv_parsing_graph.ainvoke(initial_state)
    return result
