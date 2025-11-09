"""
Unit tests for resume parser service.
"""
import pytest
import json
import os
from unittest.mock import Mock, MagicMock, patch
from services.resume_parser import parse_resume_pdf, generate_random_name


def test_generate_random_name():
    """Test random name generation."""
    name = generate_random_name()
    assert isinstance(name, str)
    assert len(name) > 0
    assert name.endswith("*")
    # Should have at least first and last name
    parts = name.split()
    assert len(parts) >= 2


@pytest.fixture
def sample_pdf_bytes():
    """Generate minimal valid PDF bytes."""
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Resume) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000306 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
390
%%EOF"""


def test_parse_resume_pdf_success(sample_pdf_bytes):
    """Test successful PDF parsing."""
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Mock successful response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "123-456-7890",
                "skills": ["Python", "FastAPI"],
                "experience": "5 years of software development",
                "education": "BS Computer Science"
            })
            mock_response.choices[0].finish_reason = "stop"
            
            mock_client.chat.completions.create.return_value = mock_response
            
            # Mock pdf2image
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                from PIL import Image
                mock_image = Image.new('RGB', (100, 100))
                mock_convert.return_value = [mock_image]
                
                result = parse_resume_pdf(sample_pdf_bytes)
                
                assert result.name == "John Doe"
                assert result.email == "john@example.com"
                assert result.phone == "123-456-7890"
                assert result.skills == ["Python", "FastAPI"]
                assert result.experience == "5 years of software development"
                assert result.education == "BS Computer Science"
                assert result.availability == "available"


def test_parse_resume_pdf_missing_openai_key(sample_pdf_bytes):
    """Test parsing when OpenAI API key is missing."""
    from config import Settings
    # Create a mock settings with empty API key
    mock_settings = Settings(openai_apikey="")
    with patch('services.resume_parser.get_settings', return_value=mock_settings):
        with pytest.raises(RuntimeError, match="OPENAI_APIKEY not found"):
            parse_resume_pdf(sample_pdf_bytes)


def test_parse_resume_pdf_openai_api_failure(sample_pdf_bytes):
    """Test parsing when OpenAI API fails."""
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("API error")
            
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                from PIL import Image
                mock_image = Image.new('RGB', (100, 100))
                mock_convert.return_value = [mock_image]
                
                # Generic Exception should bubble up (not converted to ValueError)
                with pytest.raises(Exception, match="API error"):
                    parse_resume_pdf(sample_pdf_bytes)


def test_parse_resume_pdf_invalid_pdf():
    """Test parsing with invalid PDF."""
    invalid_pdf = b"not a pdf file"
    
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI'):
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                mock_convert.side_effect = Exception("Invalid PDF")
                
                with pytest.raises(ValueError, match="Error converting PDF"):
                    parse_resume_pdf(invalid_pdf)


def test_parse_resume_pdf_empty_pdf():
    """Test parsing with empty PDF."""
    empty_pdf = b""
    
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI'):
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                mock_convert.return_value = []
                
                with pytest.raises(ValueError, match="Failed to convert PDF"):
                    parse_resume_pdf(empty_pdf)


def test_parse_resume_pdf_missing_name(sample_pdf_bytes):
    """Test parsing when name is missing (should generate random name)."""
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Response without name
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "name": "",
                "email": "john@example.com",
                "phone": "123-456-7890",
                "skills": ["Python"],
                "experience": "5 years",
                "education": "BS"
            })
            mock_response.choices[0].finish_reason = "stop"
            
            mock_client.chat.completions.create.return_value = mock_response
            
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                from PIL import Image
                mock_image = Image.new('RGB', (100, 100))
                mock_convert.return_value = [mock_image]
                
                result = parse_resume_pdf(sample_pdf_bytes)
                
                # Should generate random name with asterisk
                assert result.name.endswith("*")
                assert len(result.name) > 0


def test_parse_resume_pdf_skills_as_string(sample_pdf_bytes):
    """Test parsing when skills are provided as string instead of array."""
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Response with skills as string
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "123-456-7890",
                "skills": "Python, FastAPI, Docker",
                "experience": "5 years",
                "education": "BS"
            })
            mock_response.choices[0].finish_reason = "stop"
            
            mock_client.chat.completions.create.return_value = mock_response
            
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                from PIL import Image
                mock_image = Image.new('RGB', (100, 100))
                mock_convert.return_value = [mock_image]
                
                result = parse_resume_pdf(sample_pdf_bytes)
                
                # Should convert string to list
                assert isinstance(result.skills, list)
                assert "Python" in result.skills
                assert "FastAPI" in result.skills
                assert "Docker" in result.skills


def test_parse_resume_pdf_invalid_json_response(sample_pdf_bytes):
    """Test parsing when OpenAI returns invalid JSON."""
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Invalid JSON response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "not valid json {"
            mock_response.choices[0].finish_reason = "stop"
            
            mock_client.chat.completions.create.return_value = mock_response
            
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                from PIL import Image
                mock_image = Image.new('RGB', (100, 100))
                mock_convert.return_value = [mock_image]
                
                with pytest.raises(ValueError, match="Failed to parse OpenAI response"):
                    parse_resume_pdf(sample_pdf_bytes)


def test_parse_resume_pdf_content_filtered(sample_pdf_bytes):
    """Test parsing when OpenAI content is filtered."""
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Content filtered response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = None
            mock_response.choices[0].finish_reason = "content_filter"
            
            mock_client.chat.completions.create.return_value = mock_response
            
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                from PIL import Image
                mock_image = Image.new('RGB', (100, 100))
                mock_convert.return_value = [mock_image]
                
                with pytest.raises(ValueError, match="content policy"):
                    parse_resume_pdf(sample_pdf_bytes)


def test_parse_resume_pdf_empty_response(sample_pdf_bytes):
    """Test parsing when OpenAI returns empty response."""
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Empty response
            mock_response = MagicMock()
            mock_response.choices = []
            
            mock_client.chat.completions.create.return_value = mock_response
            
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                from PIL import Image
                mock_image = Image.new('RGB', (100, 100))
                mock_convert.return_value = [mock_image]
                
                with pytest.raises(ValueError, match="no choices"):
                    parse_resume_pdf(sample_pdf_bytes)


def test_parse_resume_pdf_missing_fields(sample_pdf_bytes):
    """Test parsing when some fields are missing (should use defaults)."""
    with patch('services.resume_parser.os.getenv', return_value="test-key"):
        with patch('services.resume_parser.OpenAI') as mock_openai_class:
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Response with missing fields
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps({
                "name": "John Doe",
                # Missing email, phone, skills, experience, education
            })
            mock_response.choices[0].finish_reason = "stop"
            
            mock_client.chat.completions.create.return_value = mock_response
            
            with patch('services.resume_parser.convert_from_bytes') as mock_convert:
                from PIL import Image
                mock_image = Image.new('RGB', (100, 100))
                mock_convert.return_value = [mock_image]
                
                result = parse_resume_pdf(sample_pdf_bytes)
                
                assert result.name == "John Doe"
                assert result.email == ""
                assert result.phone == ""
                assert result.skills == []
                assert result.experience == ""
                assert result.education == ""
                assert result.availability == "available"

