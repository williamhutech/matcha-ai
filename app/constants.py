"""Application-wide constants for Matcha AI.

This module centralizes all constants used throughout the application,
including MIME types, profile fields, timeouts, and validation limits.
"""

# Supported document types for CV parsing
SUPPORTED_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
}

# Profile field definitions
REQUIRED_PROFILE_FIELDS: list[str] = ["name", "email"]
ALL_PROFILE_FIELDS: list[str] = [
    "name",
    "email",
    "phone",
    "location",
    "current_position",
    "experience_years",
    "work_experience",
    "education",
    "skills",
    "certifications",
    "job_preference",
    "availability",
]
# Fields that should be stored as lists (comma-separated input converted)
LIST_FIELDS: list[str] = ["skills", "certifications", "languages"]

# Profile completeness threshold
MIN_PROFILE_FIELDS_FOR_COMPLETENESS: int = 3

# Retry configuration for background tasks
# Faster backoff for speed priority - only retries on transient errors anyway
DEFAULT_MAX_RETRIES: int = 2
RETRY_BACKOFF_SECONDS: list[float] = [0.5, 1.0]

# HTTP timeouts (seconds)
HTTP_TIMEOUT_CHAT: float = 60.0
HTTP_TIMEOUT_CV_PARSE: float = 120.0
HTTP_TIMEOUT_PROFILE: float = 30.0
HTTP_TIMEOUT_WHATSAPP: float = 10.0

# LLM timeout (seconds)
LLM_TIMEOUT_SECONDS: float = 45.0

# Input validation limits
MAX_MESSAGE_LENGTH: int = 4096
MAX_FILE_SIZE_MB: int = 10
