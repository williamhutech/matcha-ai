"""Security utilities for WhatsApp webhook verification."""

import hashlib
import hmac
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload: bytes, signature: str | None) -> bool:
    """
    Verify the X-Hub-Signature-256 header from Meta's webhook.

    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature:
        logger.warning("No signature provided in webhook request")
        return False

    # Signature format: "sha256=<hash>"
    if not signature.startswith("sha256="):
        logger.warning("Invalid signature format")
        return False

    expected_signature = signature[7:]  # Remove "sha256=" prefix

    # Compute HMAC-SHA256
    secret = settings.whatsapp_app_secret.encode("utf-8")
    computed_hash = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    # Compare signatures
    is_valid = hmac.compare_digest(computed_hash, expected_signature)

    if not is_valid:
        logger.warning("Webhook signature verification failed")

    return is_valid
