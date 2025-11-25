"""Shared state manager for asynchronous document parsing.

This module provides a thread-safe state container for tracking
background parsing jobs and their results.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ParsingStatus(str, Enum):
    """Status states for a parsing job."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ParsingJob:
    """Represents a single document parsing job."""

    job_id: str
    filename: str
    mime_type: str
    status: ParsingStatus = ParsingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempt: int = 0
    max_retries: int = 2
    error_message: str | None = None
    extracted_data: dict[str, Any] | None = None
    task: asyncio.Task | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        """Convert to dictionary for tool responses."""
        return {
            "job_id": self.job_id,
            "filename": self.filename,
            "status": self.status.value,
            "attempt": self.attempt,
            "error_message": self.error_message,
            "has_results": self.extracted_data is not None,
        }


class ParsingStateManager:
    """
    Manages parsing jobs for a user session.

    Thread-safe access to parsing state using asyncio locks.
    Each user session should have its own ParsingStateManager instance.
    """

    def __init__(self):
        self._jobs: dict[str, ParsingJob] = {}
        self._lock = asyncio.Lock()
        self._latest_job_id: str | None = None

    async def create_job(
        self,
        filename: str,
        mime_type: str,
        max_retries: int = 2,
    ) -> ParsingJob:
        """Create a new parsing job."""
        async with self._lock:
            job_id = str(uuid.uuid4())[:8]
            job = ParsingJob(
                job_id=job_id,
                filename=filename,
                mime_type=mime_type,
                max_retries=max_retries,
            )
            self._jobs[job_id] = job
            self._latest_job_id = job_id
            logger.info(f"Created parsing job {job_id} for {filename}")
            return job

    async def get_job(self, job_id: str) -> ParsingJob | None:
        """Get a job by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def get_latest_job(self) -> ParsingJob | None:
        """Get the most recently created job."""
        async with self._lock:
            if self._latest_job_id:
                return self._jobs.get(self._latest_job_id)
            return None

    async def update_job_status(
        self,
        job_id: str,
        status: ParsingStatus,
        error_message: str | None = None,
        extracted_data: dict | None = None,
    ) -> None:
        """Update job status and optionally set results."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                logger.warning(f"Job {job_id} not found for status update")
                return

            job.status = status

            if status == ParsingStatus.IN_PROGRESS:
                job.started_at = datetime.utcnow()
            elif status in (ParsingStatus.COMPLETED, ParsingStatus.FAILED):
                job.completed_at = datetime.utcnow()

            if error_message:
                job.error_message = error_message
            if extracted_data:
                job.extracted_data = extracted_data

            logger.info(f"Job {job_id} status updated to {status.value}")

    async def increment_attempt(self, job_id: str) -> int:
        """Increment retry attempt counter. Returns new attempt number."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.attempt += 1
                return job.attempt
            return 0

    async def can_retry(self, job_id: str) -> bool:
        """Check if job can be retried."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return job.attempt < job.max_retries
            return False

    async def set_task(self, job_id: str, task: asyncio.Task) -> None:
        """Associate an asyncio task with a job."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.task = task

    async def get_active_jobs(self) -> list[ParsingJob]:
        """Get all jobs that are currently in progress or pending."""
        async with self._lock:
            return [
                job
                for job in self._jobs.values()
                if job.status
                in (
                    ParsingStatus.PENDING,
                    ParsingStatus.IN_PROGRESS,
                    ParsingStatus.RETRYING,
                )
            ]
