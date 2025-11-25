"""LLM configuration and helpers for OpenAI."""

from langchain_openai import ChatOpenAI

from app.config import settings


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
