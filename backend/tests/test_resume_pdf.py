"""
Tests for resume PDF retrieval endpoint.
"""
import pytest
import json
import os

# Check if running in CI environment
IS_CI = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"


@pytest.mark.asyncio
@pytest.mark.skipif(IS_CI, reason="File upload tests may fail in CI due to httpx file handling differences")
async def test_get_resume_pdf_success(clean_weaviate, test_app, sample_pdf_bytes, mock_openai_resume_parser, temp_storage_dir):
    """Test getting resume PDF."""
    # Upload a resume first
    mock_openai_resume_parser.chat.completions.create.return_value.choices[0].message.content = json.dumps({
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "123-456-7890",
        "skills": ["Python"],
        "experience": "5 years",
        "education": "BS"
    })
    
    async with test_app as client:
        # Upload
        files = {"file": ("resume.pdf", sample_pdf_bytes, "application/pdf")}
        upload_response = await client.post("/api/resumes/upload", files=files)
        assert upload_response.status_code == 200, f"Upload failed with status {upload_response.status_code}: {upload_response.text}"
        resume_id = upload_response.json()["id"]
        
        # Get PDF
        response = await client.get(f"/api/resumes/{resume_id}/pdf")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0


@pytest.mark.asyncio
async def test_get_resume_pdf_not_found(test_app):
    """Test getting non-existent PDF."""
    import uuid
    fake_id = str(uuid.uuid4())
    
    async with test_app as client:
        response = await client.get(f"/api/resumes/{fake_id}/pdf")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

