"""HTTP client for calling the Matcha AI backend API."""

import os
import logging
import httpx

from app.constants import (
    HTTP_TIMEOUT_CHAT,
    HTTP_TIMEOUT_CV_PARSE,
    HTTP_TIMEOUT_PROFILE,
)

logger = logging.getLogger(__name__)

# Backend URL from environment or default to local
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")


async def chat(
    message: str,
    user_id: str,
    messages: list[dict] | None = None,
    profile_data: dict | None = None,
) -> dict:
    """
    Send a chat message to the backend API.

    Args:
        message: User message
        user_id: User identifier
        messages: Conversation history
        profile_data: Current profile data

    Returns:
        API response with response text and updated profile
    """
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_CHAT) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/chat",
            json={
                "message": message,
                "user_id": user_id,
                "messages": messages or [],
                "profile_data": profile_data or {},
            },
        )
        response.raise_for_status()
        return response.json()


async def parse_cv(
    file_content: bytes,
    filename: str,
    mime_type: str,
    user_id: str,
    profile_data: dict | None = None,
) -> dict:
    """
    Parse a CV document via the backend API.

    Args:
        file_content: File bytes
        filename: Original filename
        mime_type: MIME type
        user_id: User identifier
        profile_data: Current profile data

    Returns:
        API response with parsed data and updated profile
    """
    import json

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_CV_PARSE) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/parse-cv",
            files={"file": (filename, file_content, mime_type)},
            data={
                "user_id": user_id,
                "profile_data": json.dumps(profile_data or {}),
            },
        )
        response.raise_for_status()
        return response.json()


async def get_profile(user_id: str) -> dict:
    """
    Get user profile from the backend API.

    Args:
        user_id: User identifier

    Returns:
        User profile data
    """
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_PROFILE) as client:
        response = await client.get(f"{BACKEND_URL}/api/profile/{user_id}")
        response.raise_for_status()
        return response.json()


async def update_profile(user_id: str, profile_data: dict) -> dict:
    """
    Update user profile via the backend API.

    Args:
        user_id: User identifier
        profile_data: Profile data to save

    Returns:
        Updated profile
    """
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_PROFILE) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/profile/{user_id}",
            json=profile_data,
        )
        response.raise_for_status()
        return response.json()
