"""CV parsing utilities using Markitdown and LangChain.

This module handles:
- Document loading (PDF, DOCX)
- Text extraction via Markitdown
- Structured data extraction using LLM
"""

import logging
import tempfile
import os
from typing import Any
from pathlib import Path

from markitdown import MarkItDown
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from pydantic import ValidationError

from app.llm import create_llm
from app.assistant.prompts import CV_EXTRACTION_PROMPT
from app.constants import SUPPORTED_MIME_TYPES
from app.schema.extraction import ExtractedCV

logger = logging.getLogger(__name__)

# Initialize markitdown
markitdown_converter = MarkItDown()


async def parse_cv_from_bytes(
    content: bytes, mime_type: str, filename: str
) -> dict[str, Any]:
    """
    Parse a CV from bytes using Markitdown.

    Args:
        content: File content as bytes
        mime_type: MIME type of the document
        filename: Original filename

    Returns:
        Dictionary containing extracted profile data with confidence scores
    """
    logger.info(f"Parsing CV from bytes: {filename} ({mime_type})")

    # Check file type
    if mime_type not in SUPPORTED_MIME_TYPES:
        logger.warning(f"Unsupported file type: {mime_type}")
        return {"error": f"Unsupported file type: {mime_type}. Supported: PDF, DOCX"}

    # Extract text using markitdown
    file_ext = SUPPORTED_MIME_TYPES[mime_type]
    text = extract_text_from_bytes(content, file_ext)

    if not text:
        logger.warning("No text extracted from document")
        return {"error": "Could not extract text from document"}

    # Extract structured data using LLM
    extracted_data = await extract_structured_data(text)

    return extracted_data


def extract_text_from_bytes(content: bytes, file_ext: str) -> str:
    """
    Extract text from document bytes using Markitdown.

    Args:
        content: File content as bytes
        file_ext: File extension (pdf, docx)

    Returns:
        Extracted text as markdown
    """
    try:
        # Write to temp file (markitdown needs file path)
        with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Convert with markitdown
        result = markitdown_converter.convert(tmp_path)
        text = result.text_content.strip()

        # Cleanup
        os.unlink(tmp_path)

        # Log extraction stats for debugging
        logger.info(f"Text extraction: {len(text)} chars from {file_ext}")
        logger.debug(f"Text preview (first 200): {text[:200]}")
        logger.debug(f"Text preview (last 200): {text[-200:]}")

        # Check for skills-related content (helpful for debugging)
        if "skill" in text.lower():
            logger.debug("Skills-related content detected in extracted text")

        return text

    except Exception as e:
        logger.error(f"Error extracting text with markitdown: {e}", exc_info=True)
        return ""


async def extract_structured_data(cv_text: str) -> dict[str, Any]:
    """
    Extract structured data from CV text using LLM.

    Args:
        cv_text: Raw text extracted from CV

    Returns:
        Dictionary with extracted structured data and confidence scores
    """
    try:
        # Create the extraction chain with optimized settings
        # - temperature=0.1: Low temperature for consistent, deterministic extraction
        # - json_mode=True: Native JSON output, faster and more reliable
        # - max_tokens=16384: Max for gpt-4o-mini, handles complex CVs
        llm = create_llm(temperature=0.1, json_mode=True, max_tokens=16384)
        parser = JsonOutputParser()

        prompt = ChatPromptTemplate.from_template(CV_EXTRACTION_PROMPT)

        chain = prompt | llm | parser

        # Log what we're sending to LLM
        logger.info(f"Sending {len(cv_text)} chars to LLM for extraction")

        # Run the extraction
        raw_result = await chain.ainvoke({"cv_text": cv_text})

        # Log extraction results for debugging
        skills_count = len(raw_result.get("skills", []))
        logger.info(f"LLM extraction complete: {len(raw_result)} fields, {skills_count} skills")
        logger.debug(f"Extracted skills: {raw_result.get('skills', [])}")

        # Validate with Pydantic (flexible - allows extra fields)
        try:
            validated = ExtractedCV.model_validate(raw_result)
            logger.info("Successfully validated CV extraction with Pydantic")
            return validated.to_profile_dict()
        except ValidationError as ve:
            # Fall back to raw result if validation fails
            # This ensures we don't lose data due to schema mismatches
            logger.warning(f"Pydantic validation warning (using raw): {ve}")
            return raw_result

    except Exception as e:
        logger.error(f"Error extracting structured data: {e}", exc_info=True)
        return {
            "error": "Failed to extract structured data",
            "raw_text": cv_text[:500],
        }


async def parse_cv_from_file(file_path: str | Path) -> dict[str, Any]:
    """
    Parse a CV file and extract structured information.

    Args:
        file_path: Path to the CV file (PDF or DOCX)

    Returns:
        Dictionary containing extracted profile data with confidence scores
    """
    logger.info(f"Parsing CV from {file_path}")

    file_path = Path(file_path)

    # Determine mime type from extension
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        mime_type = "application/pdf"
    elif ext in [".docx"]:
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        return {"error": f"Unsupported file type: {ext}"}

    with open(file_path, "rb") as f:
        content = f.read()

    return await parse_cv_from_bytes(content, mime_type, file_path.name)
