"""
Unit tests for storage service.
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from storage import LocalFileStorage


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


def test_local_storage_init(temp_dir):
    """Test LocalFileStorage initialization."""
    storage = LocalFileStorage(base_dir=temp_dir)
    assert storage.base_dir == Path(temp_dir)
    assert storage.base_dir.exists()


def test_local_storage_save_pdf(temp_dir):
    """Test saving PDF file."""
    storage = LocalFileStorage(base_dir=temp_dir)
    pdf_bytes = b"fake pdf content"
    resume_id = "test-resume-123"
    
    file_path = storage.save_pdf(pdf_bytes, resume_id)
    
    assert file_path == str(Path(temp_dir) / f"{resume_id}.pdf")
    assert os.path.exists(file_path)
    
    # Verify content
    with open(file_path, "rb") as f:
        assert f.read() == pdf_bytes


def test_local_storage_get_pdf(temp_dir):
    """Test retrieving PDF file."""
    storage = LocalFileStorage(base_dir=temp_dir)
    pdf_bytes = b"fake pdf content"
    resume_id = "test-resume-123"
    
    # Save first
    storage.save_pdf(pdf_bytes, resume_id)
    
    # Retrieve
    retrieved_bytes = storage.get_pdf(resume_id)
    
    assert retrieved_bytes == pdf_bytes


def test_local_storage_get_pdf_not_found(temp_dir):
    """Test retrieving non-existent PDF."""
    storage = LocalFileStorage(base_dir=temp_dir)
    resume_id = "non-existent-123"
    
    with pytest.raises(FileNotFoundError):
        storage.get_pdf(resume_id)


def test_local_storage_get_path(temp_dir):
    """Test getting file path."""
    storage = LocalFileStorage(base_dir=temp_dir)
    resume_id = "test-resume-123"
    
    path = storage.get_path(resume_id)
    
    assert path == str(Path(temp_dir) / f"{resume_id}.pdf")
    # Path doesn't need to exist
    assert isinstance(path, str)


def test_local_storage_save_multiple_pdfs(temp_dir):
    """Test saving multiple PDFs."""
    storage = LocalFileStorage(base_dir=temp_dir)
    
    pdf1 = b"pdf content 1"
    pdf2 = b"pdf content 2"
    
    storage.save_pdf(pdf1, "resume-1")
    storage.save_pdf(pdf2, "resume-2")
    
    # Verify both exist
    assert os.path.exists(storage.get_path("resume-1"))
    assert os.path.exists(storage.get_path("resume-2"))
    
    # Verify content
    assert storage.get_pdf("resume-1") == pdf1
    assert storage.get_pdf("resume-2") == pdf2


def test_local_storage_save_overwrite(temp_dir):
    """Test overwriting existing PDF."""
    storage = LocalFileStorage(base_dir=temp_dir)
    resume_id = "test-resume-123"
    
    # Save first PDF
    pdf1 = b"original content"
    storage.save_pdf(pdf1, resume_id)
    
    # Overwrite with new PDF
    pdf2 = b"updated content"
    storage.save_pdf(pdf2, resume_id)
    
    # Verify new content
    assert storage.get_pdf(resume_id) == pdf2


def test_local_storage_directory_creation(temp_dir):
    """Test that storage creates directory if it doesn't exist."""
    new_dir = os.path.join(temp_dir, "new", "nested", "directory")
    storage = LocalFileStorage(base_dir=new_dir)
    
    # Directory should be created
    assert os.path.exists(new_dir)
    
    # Can save file
    storage.save_pdf(b"test", "resume-1")
    assert os.path.exists(storage.get_path("resume-1"))


def test_local_storage_special_characters_in_id(temp_dir):
    """Test handling of special characters in resume ID."""
    storage = LocalFileStorage(base_dir=temp_dir)
    resume_id = "test-resume_123-abc"
    
    pdf_bytes = b"test content"
    storage.save_pdf(pdf_bytes, resume_id)
    
    # Should work fine (ID is used as filename)
    assert os.path.exists(storage.get_path(resume_id))
    assert storage.get_pdf(resume_id) == pdf_bytes


def test_local_storage_empty_pdf(temp_dir):
    """Test saving empty PDF."""
    storage = LocalFileStorage(base_dir=temp_dir)
    resume_id = "empty-resume"
    
    empty_pdf = b""
    storage.save_pdf(empty_pdf, resume_id)
    
    # File should exist
    assert os.path.exists(storage.get_path(resume_id))
    
    # Content should be empty
    retrieved = storage.get_pdf(resume_id)
    assert retrieved == b""


def test_local_storage_large_pdf(temp_dir):
    """Test saving large PDF."""
    storage = LocalFileStorage(base_dir=temp_dir)
    resume_id = "large-resume"
    
    # Create large PDF content (1MB)
    large_pdf = b"x" * (1024 * 1024)
    storage.save_pdf(large_pdf, resume_id)
    
    # Verify size
    retrieved = storage.get_pdf(resume_id)
    assert len(retrieved) == len(large_pdf)
    assert retrieved == large_pdf

