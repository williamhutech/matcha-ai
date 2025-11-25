"""Supervisor agent for Matcha AI.

This module implements a ReAct-style supervisor agent that orchestrates
conversation with users, managing profile collection, CV parsing, and Q&A.
"""

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import settings
from app.assistant.tools import create_profile_tools, create_parsing_status_tools, get_service_info
from app.assistant.parsing_state import ParsingStateManager
from app.assistant.parser_agent import spawn_parser_task
from app.assistant.prompts import SUPERVISOR_SYSTEM_PROMPT
from app.constants import REQUIRED_PROFILE_FIELDS, MIN_PROFILE_FIELDS_FOR_COMPLETENESS
from app.utils import invoke_with_timeout, LLMTimeoutError

logger = logging.getLogger(__name__)


async def run_supervisor(
    messages: list,
    profile_data: dict | None = None,
    document_content: bytes | None = None,
    document_filename: str | None = None,
    document_mime: str | None = None,
    parsing_state: ParsingStateManager | None = None,
) -> dict[str, Any]:
    """
    Run the supervisor agent to process user input.

    Args:
        messages: Conversation history as list of LangChain messages
        profile_data: Current profile data dictionary (will be mutated)
        document_content: Uploaded document bytes (if any)
        document_filename: Document filename
        document_mime: Document MIME type
        parsing_state: Shared parsing state manager for async CV parsing

    Returns:
        Dictionary containing:
        - response: The agent's response text
        - profile_data: Updated profile data
        - profile_complete: Whether profile meets minimum requirements
    """
    if profile_data is None:
        profile_data = {}

    # Initialize parsing state if not provided
    if parsing_state is None:
        parsing_state = ParsingStateManager()

    # If document is uploaded, spawn background parsing task
    if document_content:
        await spawn_parser_task(
            content=document_content,
            filename=document_filename,
            mime_type=document_mime,
            state_manager=parsing_state,
        )
        logger.info(f"Spawned background parser for {document_filename}")

    # Create tools with access to state
    profile_tools = create_profile_tools(profile_data)
    parsing_tools = create_parsing_status_tools(parsing_state, profile_data)

    # Combine all tools
    tools = [
        *profile_tools,      # get_profile, update_profile_field, get_missing_fields, validate_profile
        *parsing_tools,      # is_cv_parsing_in_progress, get_parsing_status, apply_parsed_cv_data
        get_service_info,    # Q&A tool
    ]

    # Create the LLM with tool binding
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        api_key=settings.openai_api_key,
    ).bind_tools(tools)

    # Build message history with windowed context (last 10 messages)
    llm_messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)]

    # Add context about current profile state
    if profile_data:
        context = f"\n\nCurrent profile data: {profile_data}"
        llm_messages[0] = SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT + context)

    # Add conversation history (windowed)
    for msg in messages[-10:]:
        if isinstance(msg, HumanMessage):
            llm_messages.append(msg)
        elif isinstance(msg, AIMessage):
            llm_messages.append(msg)
        elif isinstance(msg, dict):
            # Handle dict format messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                llm_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                llm_messages.append(AIMessage(content=content))

    # Run the agent loop
    response_text = await _run_agent_loop(llm, tools, llm_messages)

    # Check profile completeness
    missing = [f for f in REQUIRED_PROFILE_FIELDS if not profile_data.get(f)]
    profile_complete = len(missing) == 0 and len(profile_data) >= MIN_PROFILE_FIELDS_FOR_COMPLETENESS

    return {
        "response": response_text,
        "profile_data": profile_data,
        "profile_complete": profile_complete,
    }


async def _run_agent_loop(llm, tools, messages: list, max_iterations: int = 3) -> str:
    """
    Run the ReAct agent loop until completion or max iterations.

    Args:
        llm: The language model with tools bound
        tools: List of available tools
        messages: Current message history
        max_iterations: Maximum tool-calling iterations (default: 3)

    Returns:
        Final response text from the agent
    """
    # Create tool lookup
    tool_map = {tool.name: tool for tool in tools}

    for iteration in range(max_iterations):
        # Get model response with timeout protection
        try:
            response = await invoke_with_timeout(llm, messages)
        except LLMTimeoutError:
            return "I'm having trouble processing that right now. Could you try again?"

        # Check if model wants to use tools
        if not response.tool_calls:
            # No tools called, return the response
            return response.content

        # Process tool calls
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            logger.info(f"Calling tool: {tool_name} with args: {tool_args}")

            if tool_name not in tool_map:
                tool_result = f"Error: Unknown tool '{tool_name}'"
            else:
                try:
                    tool = tool_map[tool_name]
                    # Handle async tools
                    if hasattr(tool, 'ainvoke'):
                        result = await tool.ainvoke(tool_args)
                    else:
                        result = tool.invoke(tool_args)
                    tool_result = str(result)
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
                    tool_result = f"Error calling {tool_name}: {str(e)}"

            # Add tool result to messages
            from langchain_core.messages import ToolMessage
            messages.append(ToolMessage(
                content=tool_result,
                tool_call_id=tool_call["id"],
            ))

    # Max iterations reached, get final response
    try:
        response = await invoke_with_timeout(llm, messages)
        return response.content
    except LLMTimeoutError:
        return "I'm having trouble processing that right now. Could you try again?"
