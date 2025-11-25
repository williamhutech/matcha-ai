"""Chainlit frontend application for testing Matcha AI assistant.

This provides a local web UI for testing the chat interface and document parsing.
Now uses LangGraph as the central orchestrator for all flows.
"""

import os
import logging

import chainlit as cl

from app import api_client
from app.constants import SUPPORTED_MIME_TYPES

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize a new chat session."""
    logger.info("New chat session started")

    # Initialize session state
    cl.user_session.set("messages", [])
    cl.user_session.set("profile_data", {})
    cl.user_session.set("profile_complete", False)
    cl.user_session.set("user_id", f"chainlit_user_{cl.user_session.get('id')}")

    # Send welcome message
    welcome_msg = (
        "👋 Welcome to Matcha AI!\n\n"
        "I'll help you create a job seeker profile in about 5 minutes. "
        "Your profile will be used to find personalized job matches.\n\n"
        "**Two ways to get started:**\n"
        "1. 📄 Upload your CV/resume (PDF, DOC, or DOCX) - fastest option\n"
        "2. 💬 Chat with me - I'll ask a few quick questions\n\n"
        "Which would you prefer?"
    )
    await cl.Message(content=welcome_msg).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming messages through backend API."""
    logger.info(f"Received message: {message.content[:50]}...")

    # Get session state
    messages = cl.user_session.get("messages", [])
    profile_data = cl.user_session.get("profile_data", {})
    user_id = cl.user_session.get("user_id", "session")

    # Check if message contains file attachments
    if message.elements:
        for element in message.elements:
            # Check for supported document types
            is_supported = element.mime and element.mime in SUPPORTED_MIME_TYPES

            if is_supported:
                file_ext = SUPPORTED_MIME_TYPES.get(element.mime, "document")
                logger.info(f"Processing {file_ext.upper()}: {element.name}")

                # Show processing message - parsing now happens async in background
                processing_msg = cl.Message(content="📄 Uploading your document...")
                await processing_msg.send()

                # Read file content
                document_content = element.content or open(element.path, "rb").read()

                try:
                    # Call backend API
                    result = await api_client.parse_cv(
                        file_content=document_content,
                        filename=element.name,
                        mime_type=element.mime,
                        user_id=user_id,
                        profile_data=profile_data,
                    )

                    # Update session state
                    updated_profile = result.get("profile_data", profile_data)
                    cl.user_session.set("profile_data", updated_profile)
                    cl.user_session.set("profile_complete", result.get("profile_complete", False))

                    # Update message history
                    messages.append({"role": "user", "content": f"[Uploaded: {element.name}]"})
                    messages.append({"role": "assistant", "content": result.get("response", "")})
                    cl.user_session.set("messages", messages)

                    # Send response
                    await cl.Message(content=result.get("response", "Document processed.")).send()

                except Exception as e:
                    logger.error(f"Error parsing CV: {e}", exc_info=True)
                    await cl.Message(content=f"❌ Error processing document: {str(e)}").send()

                return
            else:
                await cl.Message(
                    content=(
                        f"I can only process PDF, DOC, or DOCX files. "
                        f"You can convert your file or just chat with me instead - "
                        f"I'll ask you questions about your background."
                    )
                ).send()
                return

    # Handle text message
    if message.content:
        try:
            # Call backend API
            result = await api_client.chat(
                message=message.content,
                user_id=user_id,
                messages=messages,
                profile_data=profile_data,
            )

            # Update session state
            updated_profile = result.get("profile_data", profile_data)
            cl.user_session.set("profile_data", updated_profile)
            cl.user_session.set("profile_complete", result.get("profile_complete", False))

            # Update message history
            messages.append({"role": "user", "content": message.content})
            messages.append({"role": "assistant", "content": result.get("response", "")})
            cl.user_session.set("messages", messages)

            # Send response
            await cl.Message(content=result.get("response", "I'm not sure how to respond.")).send()

        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            error_msg = (
                "Oops! Something went wrong on my end. "
                "Please try again, or just tell me about your background directly."
            )
            await cl.Message(content=error_msg).send()


if __name__ == "__main__":
    print("Run this app with: chainlit run chainlit_app.py -w")
