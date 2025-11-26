"""Message management utilities for LangGraph agents.

This module implements token-based message trimming using a pre_model_hook
to prevent context window overflow while preserving conversation quality.

Key features:
- Accurate token counting using tiktoken (OpenAI's tokenizer)
- Preserves system message with dynamic profile context
- Uses 'llm_input_messages' key to keep full history in graph state
"""

import logging
from typing import Any, Callable

import tiktoken
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.messages.utils import trim_messages

from app.config import settings

logger = logging.getLogger(__name__)


def count_tokens_tiktoken(messages: list[BaseMessage]) -> int:
    """Count tokens using tiktoken for OpenAI models.

    This provides accurate token counting that matches OpenAI's internal
    tokenization, preventing context window overflow.

    Args:
        messages: List of LangChain messages to count tokens for

    Returns:
        Total token count including message overhead
    """
    try:
        encoding = tiktoken.encoding_for_model(settings.openai_model)
    except KeyError:
        # Fallback to cl100k_base for unknown models
        encoding = tiktoken.get_encoding("cl100k_base")

    total = 0
    for msg in messages:
        # ~4 tokens overhead per message for role, formatting
        content = str(msg.content) if msg.content else ""
        total += 4 + len(encoding.encode(content))
    return total


def create_state_modifier(
    system_prompt: str,
    profile_data_getter: Callable[[], dict] | None = None,
) -> Callable[[list[BaseMessage]], list[BaseMessage]]:
    """Create a state_modifier for LangGraph's create_react_agent.

    In LangGraph 0.2.x, state_modifier receives the messages list and
    should return a modified messages list (not a dict).

    The modifier:
    - Prepends the system message with dynamic profile context
    - Applies token-based trimming to prevent context overflow
    - Keeps most recent messages (configurable via settings)

    Args:
        system_prompt: Base system prompt for the agent
        profile_data_getter: Optional callable that returns current profile data dict

    Returns:
        A function that transforms the messages list
    """

    def state_modifier(messages: list[BaseMessage]) -> list[BaseMessage]:
        """Modify messages before sending to LLM.

        Prepends system prompt and trims to fit context window.
        """
        # Build system message with dynamic profile context
        profile_context = ""
        if profile_data_getter:
            profile_data = profile_data_getter()
            if profile_data:
                profile_context = f"\n\nCurrent user profile data:\n{profile_data}"

        full_system_prompt = system_prompt + profile_context
        system_msg = SystemMessage(content=full_system_prompt)

        # Build message list with system at start
        if messages and isinstance(messages[0], SystemMessage):
            # Replace existing system message
            all_messages = [system_msg] + list(messages[1:])
        else:
            # Prepend system message
            all_messages = [system_msg] + list(messages)

        # Token-based trimming
        trimmed = trim_messages(
            all_messages,
            strategy=settings.message_trim_strategy,
            token_counter=count_tokens_tiktoken,
            max_tokens=settings.max_context_tokens,
            start_on="human",
            end_on=("human", "tool"),
            include_system=True,
        )

        # Log trimming for debugging
        original_count = len(all_messages)
        trimmed_count = len(trimmed)
        if trimmed_count < original_count:
            logger.info(
                f"Message trimming: {original_count} -> {trimmed_count} messages "
                f"(~{count_tokens_tiktoken(trimmed)} tokens)"
            )

        return trimmed

    return state_modifier


# Alias for backwards compatibility
create_pre_model_hook = create_state_modifier
