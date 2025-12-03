"""LLM configuration and helpers for OpenAI."""

import logging

from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level cached LLM client
_cached_llm: ChatOpenAI | None = None
_llm_warmed: bool = False


def get_cached_llm() -> ChatOpenAI:
    """Get the cached LLM client, creating it if necessary."""
    global _cached_llm
    if _cached_llm is None:
        _cached_llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key,
        )
    return _cached_llm


async def warm_llm() -> bool:
    """
    Pre-warm the LLM client by initializing it.

    Returns True if warming was performed, False if already warm.
    """
    global _llm_warmed

    if _llm_warmed:
        return False

    # Initialize the cached client
    get_cached_llm()

    _llm_warmed = True
    logger.info("LLM client warmed and cached")
    return True


def is_llm_warmed() -> bool:
    """Check if the LLM client has been warmed."""
    return _llm_warmed


def create_llm(
    temperature: float | None = None,
    model: str | None = None,
    json_mode: bool = False,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """
    Create a ChatOpenAI instance with standard configuration.

    Args:
        temperature: Override default temperature
        model: Override default model
        json_mode: Enable OpenAI's native JSON response format
        max_tokens: Maximum tokens in response (None = no limit)

    Returns:
        Configured ChatOpenAI instance
    """
    kwargs = {
        "model": model or settings.openai_model,
        "temperature": temperature if temperature is not None else settings.openai_temperature,
        "api_key": settings.openai_api_key,
    }

    if json_mode:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}

    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    return ChatOpenAI(**kwargs)
