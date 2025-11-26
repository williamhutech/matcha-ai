"""REST API routes for Matcha AI backend.

These endpoints are called by the Chainlit frontend and can also be used
for other integrations. Thread IDs are used for conversation persistence
via LangGraph's checkpointer.
"""

import logging
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from app.assistant.supervisor import run_supervisor
from app.constants import SUPPORTED_MIME_TYPES, MAX_MESSAGE_LENGTH, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


# Request/Response models
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    user_id: str
    messages: list[dict] = []
    profile_data: dict = {}


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    profile_data: dict
    profile_complete: bool


class ParseCVResponse(BaseModel):
    """Response model for CV parsing endpoint."""
    response: str
    profile_data: dict
    profile_complete: bool


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat message through the supervisor agent.

    Uses thread_id based on user_id for conversation persistence
    via LangGraph's checkpointer.

    Args:
        request: Chat request with message and context

    Returns:
        Chat response with updated profile data
    """
    logger.info(f"API chat request from user {request.user_id}")

    # Input validation
    if len(request.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters."
        )

    # Use user_id as thread_id for conversation persistence
    thread_id = f"api_{request.user_id}"

    # Convert message history to LangChain format
    messages = []
    for msg in request.messages:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            messages.append(AIMessage(content=msg.get("content", "")))

    # Add current message
    messages.append(HumanMessage(content=request.message))

    try:
        result = await run_supervisor(
            messages=messages,
            profile_data=request.profile_data,
            thread_id=thread_id,
        )

        return ChatResponse(
            response=result.get("response", "I'm not sure how to respond to that."),
            profile_data=result.get("profile_data", {}),
            profile_complete=result.get("profile_complete", False),
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse-cv", response_model=ParseCVResponse)
async def parse_cv(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    profile_data: str = Form("{}"),
) -> ParseCVResponse:
    """Parse an uploaded CV document.

    Spawns background parsing via LangGraph subgraph while continuing
    the conversation. Uses thread_id for persistence.

    Args:
        file: Uploaded CV file (PDF, DOC, DOCX)
        user_id: User identifier
        profile_data: Existing profile data as JSON string

    Returns:
        Parsed CV data with updated profile
    """
    logger.info(f"API parse-cv request from user {user_id}: {file.filename}")

    # Validate file type
    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Please upload PDF, DOC, or DOCX."
        )

    # Use user_id as thread_id for conversation persistence
    thread_id = f"api_{user_id}"

    try:
        import json
        profile = json.loads(profile_data) if profile_data else {}

        # Read file content
        content = await file.read()

        # Validate file size
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB."
            )

        result = await run_supervisor(
            messages=[HumanMessage(content="I've uploaded my CV.")],
            profile_data=profile,
            document_content=content,
            document_filename=file.filename,
            document_mime=file.content_type,
            thread_id=thread_id,
        )

        return ParseCVResponse(
            response=result.get("response", "Document processed."),
            profile_data=result.get("profile_data", {}),
            profile_complete=result.get("profile_complete", False),
        )

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid profile_data JSON")
    except Exception as e:
        logger.error(f"Parse CV error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}")
async def get_profile(user_id: str) -> dict[str, Any]:
    """Get user profile data.

    Args:
        user_id: User identifier

    Returns:
        User profile data
    """
    # TODO: Implement database lookup
    # For now, return empty profile (state is managed client-side)
    return {
        "user_id": user_id,
        "profile_data": {},
        "profile_complete": False,
    }


@router.post("/profile/{user_id}")
async def update_profile(user_id: str, profile_data: dict) -> dict[str, Any]:
    """Update user profile data.

    Args:
        user_id: User identifier
        profile_data: Profile data to save

    Returns:
        Updated profile
    """
    # TODO: Implement database save
    # For now, just echo back
    return {
        "user_id": user_id,
        "profile_data": profile_data,
        "saved": True,
    }
