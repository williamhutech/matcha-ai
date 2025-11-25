"""Central configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    environment: str = "development"
    log_level: str = "INFO"

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.7

    # Supabase (optional for Chainlit testing)
    supabase_url: str | None = None
    supabase_key: str | None = None

    # WhatsApp Business API (optional for Chainlit testing)
    whatsapp_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_verify_token: str | None = None
    whatsapp_app_secret: str | None = None

    # LangSmith (optional)
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "matcha-ai"


# Global settings instance
settings = Settings()
