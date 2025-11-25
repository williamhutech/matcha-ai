"""Background document parser agent.

This module runs document parsing as a background asyncio task,
updating shared state as it progresses.
"""

import asyncio
import logging
from typing import Any

from app.documents.parsing import parse_cv_from_bytes
from app.assistant.parsing_state import (
    ParsingStateManager,
    ParsingJob,
    ParsingStatus,
)
from app.constants import RETRY_BACKOFF_SECONDS

logger = logging.getLogger(__name__)

# Error patterns that indicate transient (retryable) failures
TRANSIENT_ERROR_PATTERNS: tuple[str, ...] = (
    "timeout",
    "rate_limit",
    "rate limit",
    "connection",
    "503",
    "429",
    "502",
    "504",
    "overloaded",
    "temporarily unavailable",
    "service unavailable",
)


def is_transient_error(error: str) -> bool:
    """Check if an error is transient and worth retrying.

    Args:
        error: Error message to check

    Returns:
        True if the error is transient (network issues, rate limits, etc.)
    """
    error_lower = error.lower()
    return any(pattern in error_lower for pattern in TRANSIENT_ERROR_PATTERNS)


async def run_parser_task(
    job: ParsingJob,
    content: bytes,
    state_manager: ParsingStateManager,
) -> dict[str, Any] | None:
    """
    Execute document parsing with retry logic.

    This function runs as a background task and updates the shared state
    as parsing progresses.

    Args:
        job: The parsing job to execute
        content: Document bytes to parse
        state_manager: Shared state manager for status updates

    Returns:
        Extracted data dict on success, None on failure
    """
    job_id = job.job_id

    while True:
        attempt = await state_manager.increment_attempt(job_id)

        # Update status to in_progress or retrying
        status = ParsingStatus.RETRYING if attempt > 1 else ParsingStatus.IN_PROGRESS
        await state_manager.update_job_status(job_id, status)

        logger.info(f"Parser task starting for job {job_id}, attempt {attempt}")

        try:
            # Run the actual parsing
            extracted = await parse_cv_from_bytes(
                content=content,
                mime_type=job.mime_type,
                filename=job.filename,
            )

            # Check for extraction errors
            if "error" in extracted:
                raise ValueError(extracted["error"])

            # Success - update state with results
            await state_manager.update_job_status(
                job_id,
                ParsingStatus.COMPLETED,
                extracted_data=extracted,
            )

            logger.info(f"Parser task completed for job {job_id}")
            return extracted

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Parser task failed for job {job_id}: {error_msg}")

            # Only retry transient errors (network, rate limits, etc.)
            # Permanent errors (invalid JSON, unsupported format) fail immediately
            transient = is_transient_error(error_msg)
            can_retry = transient and await state_manager.can_retry(job_id)

            if can_retry:
                # Wait with backoff before retry
                backoff_idx = min(attempt - 1, len(RETRY_BACKOFF_SECONDS) - 1)
                backoff = RETRY_BACKOFF_SECONDS[backoff_idx]
                logger.info(f"Job {job_id} will retry in {backoff}s (transient error)")
                await asyncio.sleep(backoff)
                continue
            else:
                # Permanent error or max retries exceeded - mark as failed
                fail_reason = "permanent error" if not transient else f"{attempt} attempts"
                await state_manager.update_job_status(
                    job_id,
                    ParsingStatus.FAILED,
                    error_message=f"Failed ({fail_reason}): {error_msg}",
                )
                logger.error(f"Parser task failed permanently for job {job_id}: {fail_reason}")
                return None


async def spawn_parser_task(
    content: bytes,
    filename: str,
    mime_type: str,
    state_manager: ParsingStateManager,
) -> ParsingJob:
    """
    Spawn a background parsing task.

    Creates a job in the state manager and starts an asyncio task
    to process the document. The task will update state as it progresses.

    Args:
        content: Document bytes
        filename: Original filename
        mime_type: Document MIME type
        state_manager: Shared state manager

    Returns:
        The created ParsingJob (status will be PENDING initially)
    """
    # Create job in state manager
    job = await state_manager.create_job(
        filename=filename,
        mime_type=mime_type,
    )

    # Create and start the background task
    task = asyncio.create_task(
        run_parser_task(job, content, state_manager),
        name=f"parser_{job.job_id}",
    )

    # Store task reference for potential cancellation
    await state_manager.set_task(job.job_id, task)

    # Add error handler to prevent unhandled exceptions
    def handle_task_exception(t: asyncio.Task):
        if t.cancelled():
            logger.info(f"Parser task {job.job_id} was cancelled")
        elif t.exception():
            logger.error(
                f"Unhandled error in parser task {job.job_id}: {t.exception()}"
            )

    task.add_done_callback(handle_task_exception)

    logger.info(f"Spawned parser task for job {job.job_id}")
    return job
