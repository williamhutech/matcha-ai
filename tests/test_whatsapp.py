"""Tests for WhatsApp webhook handling."""

import pytest
from app.whatsapp import parse_webhook_payload, InternalMessage


def test_parse_text_message():
    """Test parsing a text message from WhatsApp webhook payload."""
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "1234567890",
                                    "id": "msg_123",
                                    "timestamp": "1234567890",
                                    "type": "text",
                                    "text": {"body": "Hello, world!"},
                                }
                            ],
                            "contacts": [{"wa_id": "1234567890"}],
                        }
                    }
                ]
            }
        ]
    }

    result = parse_webhook_payload(payload)

    assert result is not None
    assert isinstance(result, InternalMessage)
    assert result.whatsapp_id == "1234567890"
    assert result.message_type == "text"
    assert result.text == "Hello, world!"


def test_parse_document_message():
    """Test parsing a document message from WhatsApp webhook payload."""
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "1234567890",
                                    "id": "msg_123",
                                    "timestamp": "1234567890",
                                    "type": "document",
                                    "document": {
                                        "id": "doc_123",
                                        "mime_type": "application/pdf",
                                        "filename": "resume.pdf",
                                    },
                                }
                            ],
                            "contacts": [{"wa_id": "1234567890"}],
                        }
                    }
                ]
            }
        ]
    }

    result = parse_webhook_payload(payload)

    assert result is not None
    assert isinstance(result, InternalMessage)
    assert result.message_type == "document"
    assert result.document_filename == "resume.pdf"
    assert result.document_mime_type == "application/pdf"


def test_parse_invalid_payload():
    """Test parsing an invalid or empty payload."""
    payload = {"entry": []}

    result = parse_webhook_payload(payload)

    assert result is None


def test_parse_payload_no_messages():
    """Test parsing a payload with no messages."""
    payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}

    result = parse_webhook_payload(payload)

    assert result is None
