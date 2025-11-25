"""WhatsApp Business API webhook handling and message sending."""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel

from app.assistant.handler import handle_incoming_message
from app.config import settings
from app.security import verify_webhook_signature
from app.constants import HTTP_TIMEOUT_WHATSAPP

logger = logging.getLogger(__name__)
router = APIRouter(tags=["whatsapp"])


class InternalMessage(BaseModel):
    """Internal representation of an incoming message."""

    whatsapp_id: str  # User's WhatsApp ID
    phone_number: str  # User's phone number
    message_id: str  # WhatsApp message ID
    timestamp: str  # Message timestamp
    message_type: str  # text, document, image, etc.
    text: str | None = None  # Text content (if text message)
    document_url: str | None = None  # Document URL (if document message)
    document_mime_type: str | None = None  # Document MIME type
    document_filename: str | None = None  # Original filename


@router.get("/whatsapp")
async def verify_webhook(
    request: Request,
):
    """Handle WhatsApp webhook verification challenge from Meta."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None),
):
    """Handle incoming WhatsApp webhook events."""
    body = await request.body()

    # Verify webhook signature
    if not verify_webhook_signature(body, x_hub_signature_256):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    logger.debug(f"Received webhook payload: {payload}")

    # Parse the webhook payload
    try:
        internal_message = parse_webhook_payload(payload)
        if internal_message:
            # Process the message through the assistant
            reply = await handle_incoming_message(internal_message)

            # Send reply back to user
            await send_whatsapp_message(internal_message.phone_number, reply)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Return 200 to avoid Meta retries on application errors
        return {"status": "error"}

    return {"status": "ok"}


def parse_webhook_payload(payload: dict[str, Any]) -> InternalMessage | None:
    """
    Parse WhatsApp webhook payload into InternalMessage.

    Returns None if the payload doesn't contain a message we can process.
    """
    try:
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return None

        message = messages[0]
        contacts = value.get("contacts", [])
        contact = contacts[0] if contacts else {}

        whatsapp_id = message.get("from")
        phone_number = contact.get("wa_id", whatsapp_id)
        message_id = message.get("id")
        timestamp = message.get("timestamp")
        message_type = message.get("type")

        internal_msg = InternalMessage(
            whatsapp_id=whatsapp_id,
            phone_number=phone_number,
            message_id=message_id,
            timestamp=timestamp,
            message_type=message_type,
        )

        # Extract content based on message type
        if message_type == "text":
            internal_msg.text = message.get("text", {}).get("body", "")

        elif message_type == "document":
            doc = message.get("document", {})
            internal_msg.document_url = doc.get("id")  # Media ID, needs to be downloaded
            internal_msg.document_mime_type = doc.get("mime_type")
            internal_msg.document_filename = doc.get("filename")

        # Add more message types as needed (image, audio, etc.)

        return internal_msg

    except (IndexError, KeyError) as e:
        logger.warning(f"Failed to parse webhook payload: {e}")
        return None


async def send_whatsapp_message(to: str, text: str) -> bool:
    """
    Send a text message via WhatsApp Cloud API.

    Args:
        to: Recipient's phone number (with country code, no +)
        text: Message text to send

    Returns:
        True if successful, False otherwise
    """
    url = f"https://graph.facebook.com/v18.0/{settings.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_WHATSAPP)
            response.raise_for_status()
            logger.info(f"Message sent successfully to {to}")
            return True

    except httpx.HTTPError as e:
        logger.error(f"Failed to send WhatsApp message: {e}", exc_info=True)
        return False
