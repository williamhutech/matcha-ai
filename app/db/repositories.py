"""Data access layer - repositories for database operations.

This module provides a clean interface for all database operations:
- User CRUD
- Profile CRUD
- Experience, Education, Language operations
- Document and extraction management
- Message logging

NOTE: These functions are currently stubs pending database implementation.
Session state is currently managed in-memory via handler.py and routes.py.
When database support is added, implement the Supabase calls in each function.
"""

import logging
from typing import Any
from datetime import datetime

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


# ============================================================================
# User Operations
# ============================================================================


async def get_or_create_user_by_whatsapp(
    whatsapp_id: str, phone_number: str
) -> dict[str, Any]:
    """
    Get existing user or create a new one by WhatsApp ID.

    Args:
        whatsapp_id: User's WhatsApp ID
        phone_number: User's phone number

    Returns:
        User record as dict
    """
    # TODO: Implement with actual database schema
    # Check if user exists
    # response = supabase.table("users").select("*").eq("whatsapp_id", whatsapp_id).execute()
    #
    # if response.data:
    #     return response.data[0]
    #
    # # Create new user
    # new_user = {
    #     "whatsapp_id": whatsapp_id,
    #     "phone_number": phone_number,
    #     "created_at": datetime.utcnow().isoformat(),
    # }
    # response = supabase.table("users").insert(new_user).execute()
    # return response.data[0]

    logger.info(f"get_or_create_user_by_whatsapp called for {whatsapp_id}")
    return {"id": "placeholder_user_id", "whatsapp_id": whatsapp_id}


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """
    Get user by ID.

    Args:
        user_id: User's database ID

    Returns:
        User record or None if not found
    """
    # TODO: Implement
    # response = supabase.table("users").select("*").eq("id", user_id).execute()
    # return response.data[0] if response.data else None

    logger.info(f"get_user_by_id called for {user_id}")
    return None


# ============================================================================
# Profile Operations
# ============================================================================


async def get_profile(user_id: str) -> dict[str, Any] | None:
    """
    Get user's profile.

    Args:
        user_id: User's database ID

    Returns:
        Profile record or None if not found
    """
    # TODO: Implement
    # response = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    # return response.data[0] if response.data else None

    logger.info(f"get_profile called for user {user_id}")
    return None


async def upsert_profile_fields(user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """
    Update or insert profile fields.

    Args:
        user_id: User's database ID
        fields: Dictionary of field names and values to update

    Returns:
        Updated profile record
    """
    # TODO: Implement
    # fields["user_id"] = user_id
    # fields["updated_at"] = datetime.utcnow().isoformat()
    #
    # response = (
    #     supabase.table("profiles")
    #     .upsert(fields, on_conflict="user_id")
    #     .execute()
    # )
    # return response.data[0]

    logger.info(f"upsert_profile_fields called for user {user_id} with fields: {fields}")
    return {"user_id": user_id, **fields}


# ============================================================================
# Experience Operations
# ============================================================================


async def create_experience(user_id: str, experience: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new work experience record.

    Args:
        user_id: User's database ID
        experience: Experience data (company, title, dates, description, etc.)

    Returns:
        Created experience record
    """
    # TODO: Implement
    # experience["user_id"] = user_id
    # experience["created_at"] = datetime.utcnow().isoformat()
    #
    # response = supabase.table("experiences").insert(experience).execute()
    # return response.data[0]

    logger.info(f"create_experience called for user {user_id}")
    return {"id": "placeholder_experience_id", "user_id": user_id, **experience}


async def get_experiences(user_id: str) -> list[dict[str, Any]]:
    """
    Get all work experiences for a user.

    Args:
        user_id: User's database ID

    Returns:
        List of experience records
    """
    # TODO: Implement
    # response = supabase.table("experiences").select("*").eq("user_id", user_id).execute()
    # return response.data

    logger.info(f"get_experiences called for user {user_id}")
    return []


# ============================================================================
# Education Operations
# ============================================================================


async def create_education(user_id: str, education: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new education record.

    Args:
        user_id: User's database ID
        education: Education data (institution, degree, dates, etc.)

    Returns:
        Created education record
    """
    # TODO: Implement
    logger.info(f"create_education called for user {user_id}")
    return {"id": "placeholder_education_id", "user_id": user_id, **education}


async def get_educations(user_id: str) -> list[dict[str, Any]]:
    """
    Get all education records for a user.

    Args:
        user_id: User's database ID

    Returns:
        List of education records
    """
    # TODO: Implement
    logger.info(f"get_educations called for user {user_id}")
    return []


# ============================================================================
# Language Operations
# ============================================================================


async def create_language(user_id: str, language: dict[str, Any]) -> dict[str, Any]:
    """
    Create a new language proficiency record.

    Args:
        user_id: User's database ID
        language: Language data (language name, proficiency level)

    Returns:
        Created language record
    """
    # TODO: Implement
    logger.info(f"create_language called for user {user_id}")
    return {"id": "placeholder_language_id", "user_id": user_id, **language}


async def get_languages(user_id: str) -> list[dict[str, Any]]:
    """
    Get all language proficiencies for a user.

    Args:
        user_id: User's database ID

    Returns:
        List of language records
    """
    # TODO: Implement
    logger.info(f"get_languages called for user {user_id}")
    return []


# ============================================================================
# Document Operations
# ============================================================================


async def create_document(user_id: str, document: dict[str, Any]) -> dict[str, Any]:
    """
    Create a document record (uploaded CV/resume).

    Args:
        user_id: User's database ID
        document: Document metadata (filename, mime_type, url, etc.)

    Returns:
        Created document record
    """
    # TODO: Implement
    logger.info(f"create_document called for user {user_id}")
    return {"id": "placeholder_document_id", "user_id": user_id, **document}


async def create_document_extraction(
    document_id: str, extraction: dict[str, Any]
) -> dict[str, Any]:
    """
    Store extracted data from a document.

    Args:
        document_id: Document's database ID
        extraction: Extracted data and metadata

    Returns:
        Created extraction record
    """
    # TODO: Implement
    logger.info(f"create_document_extraction called for document {document_id}")
    return {"id": "placeholder_extraction_id", "document_id": document_id, **extraction}


# ============================================================================
# Message Logging
# ============================================================================


async def log_message(
    user_id: str,
    direction: str,  # "inbound" or "outbound"
    message_type: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Log a message for audit trail and debugging.

    Args:
        user_id: User's database ID
        direction: "inbound" or "outbound"
        message_type: Type of message (text, document, etc.)
        content: Message content
        metadata: Additional metadata (message_id, timestamp, etc.)

    Returns:
        Created message log record
    """
    # TODO: Implement
    logger.info(f"log_message called: {direction} {message_type} for user {user_id}")
    return {
        "id": "placeholder_message_id",
        "user_id": user_id,
        "direction": direction,
        "message_type": message_type,
        "content": content,
        "metadata": metadata,
    }
