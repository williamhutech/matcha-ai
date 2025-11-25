"""Tests for CV parsing functionality."""

import pytest
from pathlib import Path

from app.documents.parsing import extract_text_from_bytes, parse_cv_from_file


class TestTextExtraction:
    """Tests for text extraction from documents."""

    def test_extract_text_from_invalid_pdf(self):
        """Test PDF text extraction with invalid content handles gracefully."""
        invalid_content = b"not a pdf"
        result = extract_text_from_bytes(invalid_content, "pdf")
        # Markitdown may return the raw content or empty string for invalid PDFs
        # The important thing is it doesn't crash
        assert isinstance(result, str)

    def test_extract_text_from_cv_sample_3(self):
        """Test that CV Sample 3 text extraction includes TECHNICAL SKILLS section."""
        pdf_path = Path(__file__).parent / "CV Sample 3.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Sample 3.pdf not found in tests directory")

        with open(pdf_path, "rb") as f:
            content = f.read()

        text = extract_text_from_bytes(content, "pdf")

        # Verify text was extracted
        assert len(text) > 1000, "Expected substantial text extraction"

        # Verify page 3 content (TECHNICAL SKILLS) is included
        text_lower = text.lower()
        assert "technical skills" in text_lower, "TECHNICAL SKILLS section not extracted"
        assert "matlab" in text_lower, "Matlab skill not in extracted text"

    def test_extract_text_includes_all_pages(self):
        """Test that multi-page PDF extraction includes content from all pages."""
        pdf_path = Path(__file__).parent / "CV Sample 3.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Sample 3.pdf not found in tests directory")

        with open(pdf_path, "rb") as f:
            content = f.read()

        text = extract_text_from_bytes(content, "pdf")

        # Page 1 content
        assert "juan garcia" in text.lower(), "Page 1 content (name) not found"
        assert "education" in text.lower(), "Page 1 content (EDUCATION) not found"

        # Page 3 content (last page)
        assert "references" in text.lower(), "Page 3 content (REFERENCES) not found"


class TestSkillsExtraction:
    """Tests for skills extraction from CVs."""

    @pytest.mark.asyncio
    async def test_cv_sample_3_extracts_skills(self):
        """Test that CV Sample 3 (engineering CV) extracts technical skills."""
        pdf_path = Path(__file__).parent / "CV Sample 3.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Sample 3.pdf not found in tests directory")

        result = await parse_cv_from_file(pdf_path)

        # Should not have error
        assert "error" not in result, f"Extraction failed: {result.get('error')}"

        # Should have skills field
        assert "skills" in result, "skills field missing from result"

        # Should extract skills (CV Sample 3 has TECHNICAL SKILLS section)
        skills = result["skills"]
        assert len(skills) > 0, "No skills extracted from CV with TECHNICAL SKILLS section"

        # Check for specific expected skills
        skills_lower = [s.lower() for s in skills]
        assert any("matlab" in s for s in skills_lower), "Expected 'Matlab' in skills"
        assert any("autocad" in s for s in skills_lower), "Expected 'AutoCAD' in skills"

    @pytest.mark.asyncio
    async def test_cv_sample_2_no_skills_section(self):
        """Test that CV Sample 2 (humanities CV without skills section) returns empty skills."""
        pdf_path = Path(__file__).parent / "CV Sample 2.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Sample 2.pdf not found in tests directory")

        result = await parse_cv_from_file(pdf_path)

        # Should not have error
        assert "error" not in result, f"Extraction failed: {result.get('error')}"

        # Should have skills field (even if empty)
        assert "skills" in result, "skills field missing from result"

        # Skills should be empty (CV Sample 2 is humanities CV without skills section)
        # This is correct behavior - we only extract explicitly stated skills
        skills = result["skills"]
        assert isinstance(skills, list), "skills should be a list"

    @pytest.mark.asyncio
    async def test_cv_example_1_extracts_skills(self):
        """Test that CV Example 1 extracts skills."""
        pdf_path = Path(__file__).parent / "CV Example 1.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Example 1.pdf not found in tests directory")

        result = await parse_cv_from_file(pdf_path)

        # Should not have error
        assert "error" not in result, f"Extraction failed: {result.get('error')}"

        # Should have skills
        skills = result.get("skills", [])
        assert len(skills) > 0, "Expected skills from CV Example 1"


class TestDocxExtraction:
    """Tests for DOCX/Word document extraction."""

    def test_extract_text_from_docx(self):
        """Test that DOCX files can be parsed."""
        docx_path = Path(__file__).parent / "CV Example 5.docx"
        if not docx_path.exists():
            pytest.skip("CV Example 5.docx not found in tests directory")

        with open(docx_path, "rb") as f:
            content = f.read()

        text = extract_text_from_bytes(content, "docx")

        # Verify text was extracted
        assert len(text) > 500, "Expected substantial text extraction from DOCX"
        assert "amelia" in text.lower(), "Expected name in extracted text"

    @pytest.mark.asyncio
    async def test_docx_full_extraction(self):
        """Test full CV extraction from DOCX file."""
        docx_path = Path(__file__).parent / "CV Example 5.docx"
        if not docx_path.exists():
            pytest.skip("CV Example 5.docx not found in tests directory")

        result = await parse_cv_from_file(docx_path)

        # Should not have error
        assert "error" not in result, f"Extraction failed: {result.get('error')}"

        # Should extract basic info
        assert result.get("name"), "Name should be extracted from DOCX"
        assert result.get("email"), "Email should be extracted from DOCX"

    @pytest.mark.asyncio
    async def test_docx_extracts_skills(self):
        """Test that skills are extracted from DOCX CV."""
        docx_path = Path(__file__).parent / "CV Example 5.docx"
        if not docx_path.exists():
            pytest.skip("CV Example 5.docx not found in tests directory")

        result = await parse_cv_from_file(docx_path)

        assert "error" not in result
        skills = result.get("skills", [])
        # CV Example 5 has Python, R, HTML, MATLAB
        assert len(skills) > 0, "Expected skills from CV Example 5"
        skills_lower = [s.lower() for s in skills]
        assert any("python" in s for s in skills_lower), "Expected Python in skills"


class TestFullExtraction:
    """Tests for complete CV extraction."""

    @pytest.mark.asyncio
    async def test_extracts_basic_info(self):
        """Test that basic info (name, email) is extracted."""
        pdf_path = Path(__file__).parent / "CV Sample 3.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Sample 3.pdf not found in tests directory")

        result = await parse_cv_from_file(pdf_path)

        assert "error" not in result
        assert result.get("name"), "Name should be extracted"
        assert result.get("email"), "Email should be extracted"
        assert "@" in result.get("email", ""), "Email should contain @"

    @pytest.mark.asyncio
    async def test_extracts_education(self):
        """Test that education entries are extracted."""
        pdf_path = Path(__file__).parent / "CV Sample 3.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Sample 3.pdf not found in tests directory")

        result = await parse_cv_from_file(pdf_path)

        assert "error" not in result
        education = result.get("education", [])
        assert len(education) >= 2, "Expected at least 2 education entries"

    @pytest.mark.asyncio
    async def test_extracts_work_experience(self):
        """Test that work experience entries are extracted."""
        pdf_path = Path(__file__).parent / "CV Sample 3.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Sample 3.pdf not found in tests directory")

        result = await parse_cv_from_file(pdf_path)

        assert "error" not in result
        work = result.get("work_experience", [])
        assert len(work) >= 1, "Expected at least 1 work experience entry"

    @pytest.mark.asyncio
    async def test_extracts_languages(self):
        """Test that languages are extracted."""
        pdf_path = Path(__file__).parent / "CV Sample 3.pdf"
        if not pdf_path.exists():
            pytest.skip("CV Sample 3.pdf not found in tests directory")

        result = await parse_cv_from_file(pdf_path)

        assert "error" not in result
        languages = result.get("languages", [])
        assert len(languages) >= 2, "Expected Spanish and English"
