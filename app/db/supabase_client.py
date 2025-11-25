"""Supabase client initialization and configuration."""

import logging

from supabase import create_client, Client

from app.config import settings

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.

    Returns:
        Configured Supabase client
    """
    try:
        client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
        raise


# Global client instance
supabase: Client = get_supabase_client()
