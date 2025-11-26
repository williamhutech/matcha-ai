"""Supervisor agent for Matcha AI using LangGraph prebuilt agents.

This module implements the main conversation agent using LangGraph's
create_react_agent for a production-ready implementation with:
- Automatic message history management
- Thread-based persistence via checkpointer
- Token-based context trimming
- Background CV parsing via LangGraph subgraph
"""

import asyncio
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.assistant.tools import create_all_tools
from app.assistant.prompts import SUPERVISOR_SYSTEM_PROMPT
from app.assistant.cv_parsing_graph import (
    invoke_cv_parsing,
    ParsingStatus,
)
from app.constants import REQUIRED_PROFILE_FIELDS, MIN_PROFILE_FIELDS_FOR_COMPLETENESS

logger = logging.getLogger(__name__)

# Module-level checkpointer (InMemorySaver for now)
# This provides persistence across conversation turns within the same session
_checkpointer = MemorySaver()

# Track background parsing tasks per thread_id
# This enables the hybrid approach: LangGraph subgraph + background execution
_parsing_tasks: dict[str, asyncio.Task] = {}
_parsing_results: dict[str, dict] = {}


async def _run_cv_parsing_background(
    thread_id: str,
    content: bytes,
    filename: str,
    mime_type: str,
) -> None:
    """Run CV parsing in background and store results.

    This wraps the LangGraph subgraph invocation in an asyncio task,
    enabling non-blocking document processing while conversation continues.

    Args:
        thread_id: Thread identifier for storing results
        content: Document bytes
        filename: Original filename
        mime_type: Document MIME type
    """
    try:
        logger.info(f"Starting background CV parsing for '{filename}' (thread: {thread_id})")
        result = await invoke_cv_parsing(
            content=content,
            filename=filename,
            mime_type=mime_type,
        )
        _parsing_results[thread_id] = result
        logger.info(f"CV parsing completed for '{filename}': {result.get('status')}")
    except Exception as e:
        logger.error(f"Background CV parsing failed: {e}", exc_info=True)
        _parsing_results[thread_id] = {
            "status": ParsingStatus.FAILED,
            "error_message": str(e),
            "document_filename": filename,
            "extracted_data": None,
        }


def _is_parsing_in_progress(thread_id: str) -> bool:
    """Check if parsing is currently running for a thread."""
    task = _parsing_tasks.get(thread_id)
    return task is not None and not task.done()


def _check_profile_complete(profile_data: dict) -> bool:
    """Check if profile meets minimum completeness requirements."""
    missing = [f for f in REQUIRED_PROFILE_FIELDS if not profile_data.get(f)]
    return len(missing) == 0 and len(profile_data) >= MIN_PROFILE_FIELDS_FOR_COMPLETENESS


async def run_supervisor(
    messages: list,
    profile_data: dict | None = None,
    document_content: bytes | None = None,
    document_filename: str | None = None,
    document_mime: str | None = None,
    thread_id: str = "default",
) -> dict[str, Any]:
    """Run the supervisor agent to process user input.

    This function uses LangGraph's create_react_agent for a clean,
    production-ready agent implementation with automatic tool calling,
    message management, and session persistence.

    Args:
        messages: Conversation history as list of LangChain messages
        profile_data: Current profile data dictionary (will be mutated)
        document_content: Uploaded document bytes (if any)
        document_filename: Document filename
        document_mime: Document MIME type
        thread_id: Unique conversation thread ID (e.g., "whatsapp_+1234567890")

    Returns:
        Dictionary containing:
        - response: The agent's response text
        - profile_data: Updated profile data
        - profile_complete: Whether profile meets minimum requirements
    """
    if profile_data is None:
        profile_data = {}

    # Handle document upload - spawn background parsing task
    if document_content and document_filename and document_mime:
        # Cancel any existing parsing task for this thread
        existing_task = _parsing_tasks.get(thread_id)
        if existing_task and not existing_task.done():
            existing_task.cancel()
            logger.info(f"Cancelled previous parsing task for thread {thread_id}")

        # Spawn new background parsing task
        task = asyncio.create_task(
            _run_cv_parsing_background(
                thread_id=thread_id,
                content=document_content,
                filename=document_filename,
                mime_type=document_mime,
            )
        )
        _parsing_tasks[thread_id] = task
        logger.info(f"Spawned background parser for '{document_filename}' (thread: {thread_id})")

    # Check for completed parsing results and apply to profile
    parsing_result = _parsing_results.get(thread_id)
    if parsing_result and parsing_result.get("status") == ParsingStatus.COMPLETED:
        extracted = parsing_result.get("extracted_data", {})
        if extracted:
            applied_count = 0
            for key, value in extracted.items():
                # Skip metadata fields
                if key in ["error", "raw_text", "confidence_scores", "missing_fields"]:
                    continue
                if value is not None:
                    profile_data[key] = value
                    applied_count += 1
            if applied_count > 0:
                logger.info(f"Applied {applied_count} fields from CV parsing to profile")

    # Determine parsing state for tools
    parsing_in_progress = _is_parsing_in_progress(thread_id)

    # Create tools with current state (tools capture state via closure)
    tools = create_all_tools(
        profile_data=profile_data,
        parsing_results=parsing_result,
        parsing_in_progress=parsing_in_progress,
    )

    # Create LLM
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        api_key=settings.openai_api_key,
    )

    # Build system prompt with current profile context
    profile_context = ""
    if profile_data:
        profile_context = f"\n\nCurrent user profile data:\n{profile_data}"
    full_system_prompt = SUPERVISOR_SYSTEM_PROMPT + profile_context

    # Create agent using LangGraph's prebuilt create_react_agent
    # Using 'prompt' parameter for system prompt (simpler than state_modifier)
    agent = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=_checkpointer,
        prompt=full_system_prompt,  # System prompt with profile context
    )

    # Build config with thread_id for persistence
    config = {"configurable": {"thread_id": thread_id}}

    # Normalize messages to LangChain format
    normalized_messages = []
    for msg in messages:
        if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
            normalized_messages.append(msg)
        elif isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                normalized_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                normalized_messages.append(AIMessage(content=content))

    # Invoke agent
    try:
        result = await agent.ainvoke(
            {"messages": normalized_messages},
            config=config,
        )

        # Extract response from last AI message (that isn't a tool call)
        response_text = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                # Skip messages that are just tool calls
                if msg.tool_calls:
                    continue
                if msg.content:
                    response_text = msg.content
                    break

        if not response_text:
            response_text = "I'm not sure how to respond to that. Could you rephrase?"

        return {
            "response": response_text,
            "profile_data": profile_data,
            "profile_complete": _check_profile_complete(profile_data),
        }

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return {
            "response": "I'm having trouble processing that right now. Could you try again?",
            "profile_data": profile_data,
            "profile_complete": _check_profile_complete(profile_data),
        }
