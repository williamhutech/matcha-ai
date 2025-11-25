"""Shared utility functions for Matcha AI.

This module contains utility functions for:
- Message format conversion
- Input validation (file uploads, email)
- Profile completeness checking
- LLM invocation with timeout protection
"""

import asyncio
import logging

from langchain_core.messages import HumanMessage, AIMessage

from app.constants import (
    SUPPORTED_MIME_TYPES,
    MAX_FILE_SIZE_MB,
    REQUIRED_PROFILE_FIELDS,
    MIN_PROFILE_FIELDS_FOR_COMPLETENESS,
    LLM_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


# --- LLM Utilities ---

class LLMTimeoutError(Exception):
    """Raised when LLM call times out."""
    pass


async def invoke_with_timeout(
    llm,
    messages: list,
    timeout_seconds: float | None = None,
):
    """
    Invoke LLM with timeout protection.

    Args:
        llm: The LangChain LLM instance
        messages: List of messages to send
        timeout_seconds: Timeout in seconds (defaults to LLM_TIMEOUT_SECONDS)

    Returns:
        LLM response

    Raises:
        LLMTimeoutError: If the call times out
    """
    if timeout_seconds is None:
        timeout_seconds = LLM_TIMEOUT_SECONDS

    try:
        return await asyncio.wait_for(
            llm.ainvoke(messages),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.error(f"LLM call timed out after {timeout_seconds}s")
        raise LLMTimeoutError(f"Request timed out after {timeout_seconds} seconds")


# --- Input Validation ---

def is_supported_document(mime_type: str) -> bool:
    """Check if MIME type is a supported document format."""
    return mime_type in SUPPORTED_MIME_TYPES


def get_file_extension(mime_type: str) -> str | None:
    """Get file extension for a MIME type."""
    return SUPPORTED_MIME_TYPES.get(mime_type)


def validate_file_upload(mime_type: str, size_bytes: int) -> tuple[bool, str | None]:
    """
    Validate file upload.

    Args:
        mime_type: MIME type of the file
        size_bytes: File size in bytes

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid.
    """
    if not is_supported_document(mime_type):
        return False, "Unsupported file type. Please upload PDF, DOC, or DOCX."

    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB."

    return True, None


def validate_email(email: str) -> bool:
    """Basic email format validation."""
    return "@" in email and "." in email.split("@")[-1]


# --- Message Conversion ---

def convert_messages_to_langchain(messages: list[dict]) -> list:
    """
    Convert message dictionaries to LangChain message format.

    Args:
        messages: List of message dicts with 'role' and 'content' keys

    Returns:
        List of LangChain HumanMessage/AIMessage objects
    """
    result = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))

    return result


# --- Profile Utilities ---

def is_profile_complete(profile_data: dict, required_fields: list[str] | None = None) -> bool:
    """
    Check if a profile has all required fields.

    Args:
        profile_data: Dictionary containing profile data
        required_fields: List of required field names (defaults to REQUIRED_PROFILE_FIELDS)

    Returns:
        True if all required fields are present and profile has minimum data
    """
    if required_fields is None:
        required_fields = REQUIRED_PROFILE_FIELDS

    # Check required fields
    for field in required_fields:
        if not profile_data.get(field):
            return False

    # Require minimum number of fields for a useful profile
    return len(profile_data) >= MIN_PROFILE_FIELDS_FOR_COMPLETENESS
