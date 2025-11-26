"""Main handler for incoming messages - the assistant's 'brain' entry point.

This module handles WhatsApp messages by routing them to the supervisor agent
with thread-based persistence for conversation continuity.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, AIMessage

from app.assistant.supervisor import run_supervisor

if TYPE_CHECKING:
    from app.whatsapp import InternalMessage

logger = logging.getLogger(__name__)

# In-memory session storage for WhatsApp users
# Profile data is stored here; conversation history is managed by LangGraph checkpointer
# TODO: Replace with database persistence
_user_sessions: dict[str, dict] = {}


def get_user_session(phone_number: str) -> dict:
    """Get or create a session for a user.

    Note: Conversation history is now managed by LangGraph's checkpointer
    via thread_id. We only store profile_data and message list locally.
    """
    if phone_number not in _user_sessions:
        _user_sessions[phone_number] = {
            "messages": [],
            "profile_data": {},
        }
    return _user_sessions[phone_number]


async def handle_incoming_message(message: "InternalMessage") -> str:
    """Process an incoming message and return a reply.

    This is the main entry point called by the WhatsApp webhook handler.
    It orchestrates the supervisor agent and returns a response.

    Args:
        message: Parsed internal message from WhatsApp

    Returns:
        Reply text to send back to the user
    """
    logger.info(
        f"Processing message from {message.phone_number}, type: {message.message_type}"
    )

    # Use phone number as thread_id for conversation persistence
    thread_id = f"whatsapp_{message.phone_number}"

    # Get user session for profile data
    session = get_user_session(message.phone_number)
    messages = session["messages"]
    profile_data = session["profile_data"]

    try:
        if message.message_type == "text" and message.text:
            # Add user message to history
            messages.append(HumanMessage(content=message.text))

            # Run supervisor agent with thread_id for persistence
            result = await run_supervisor(
                messages=messages,
                profile_data=profile_data,
                thread_id=thread_id,
            )

            # Update session with results
            session["profile_data"] = result.get("profile_data", profile_data)

            # Add assistant response to history
            response = result.get("response", "I'm not sure how to respond to that.")
            messages.append(AIMessage(content=response))

            return response

        elif message.message_type == "document":
            # Handle document uploads (CV parsing)
            # TODO: Download document from WhatsApp media API
            # For now, inform user we received it

            if message.document_filename:
                # Add context message
                messages.append(HumanMessage(content=f"I've uploaded my CV: {message.document_filename}"))

                # Note: Actual document parsing requires downloading the media
                # from WhatsApp's API using message.document_id
                return (
                    f"I received your document '{message.document_filename}'. "
                    "Document processing via WhatsApp is coming soon! "
                    "For now, please try uploading through our web interface."
                )
            else:
                return "I received a document but couldn't get the filename. Please try again."

        else:
            return f"I received a {message.message_type} message. I currently support text messages and document uploads."

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return "Sorry, I encountered an error processing your message. Please try again."
