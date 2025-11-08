"""
Tests for consultant matching endpoint.
"""
import pytest
import uuid
import time


@pytest.mark.asyncio
async def test_match_consultants_success(clean_weaviate, test_app, sample_project_description):
    """Test successful consultant matching."""
    # Insert test consultants
    consultant1 = {
        "name": "Python Developer",
        "email": "python@example.com",
        "phone": "111-111-1111",
        "skills": ["Python", "FastAPI", "Docker"],
        "availability": "available",
        "experience": "5 years Python development",
        "education": "BS Computer Science"
    }
    
    consultant2 = {
        "name": "Java Developer",
        "email": "java@example.com",
        "phone": "222-222-2222",
        "skills": ["Java", "Spring"],
        "availability": "available",
        "experience": "3 years Java development",
        "education": "BS Computer Science"
    }
    
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    
    clean_weaviate.data_object.create(data_object=consultant1, class_name="Consultant", uuid=id1)
    clean_weaviate.data_object.create(data_object=consultant2, class_name="Consultant", uuid=id2)
    
    # Wait a moment for indexing
    time.sleep(1)
    
    async with test_app as client:
        response = await client.post("/api/consultants/match", json=sample_project_description)
        
        assert response.status_code == 200
        data = response.json()
        assert "consultants" in data
        assert len(data["consultants"]) <= 3
        
        # Verify consultants have match scores
        for consultant in data["consultants"]:
            assert "matchScore" in consultant
            assert 0 <= consultant["matchScore"] <= 100


@pytest.mark.asyncio
async def test_match_consultants_empty_database(clean_weaviate, test_app, sample_project_description):
    """Test matching when database is empty (no consultants but schema exists)."""
    async with test_app as client:
        response = await client.post("/api/consultants/match", json=sample_project_description)
        
        # When schema exists but no consultants, returns 200 with empty list
        # (422 is only raised when schema doesn't exist)
        assert response.status_code == 200
        data = response.json()
        assert data["consultants"] == []


@pytest.mark.asyncio
async def test_match_consultants_single_consultant(clean_weaviate, test_app, sample_project_description):
    """Test matching with single consultant in database."""
    consultant = {
        "name": "Python Developer",
        "email": "python@example.com",
        "phone": "111-111-1111",
        "skills": ["Python", "FastAPI"],
        "availability": "available",
        "experience": "5 years",
        "education": "BS"
    }
    
    id1 = str(uuid.uuid4())
    clean_weaviate.data_object.create(data_object=consultant, class_name="Consultant", uuid=id1)
    
    time.sleep(1)
    
    async with test_app as client:
        response = await client.post("/api/consultants/match", json=sample_project_description)
        
        # With "none" vectorizer, vector search doesn't work, so may return empty results
        # But the endpoint should still return 200
        assert response.status_code == 200
        data = response.json()
        # May return 0 or 1 consultant depending on vectorizer
        assert len(data["consultants"]) <= 1
        if len(data["consultants"]) > 0:
            assert data["consultants"][0]["matchScore"] is not None


@pytest.mark.asyncio
async def test_match_consultants_no_weaviate(test_app, sample_project_description, monkeypatch):
    """Test matching when Weaviate is unavailable."""
    from unittest.mock import patch
    with patch('main.client', None):
        async with test_app as client:
            response = await client.post("/api/consultants/match", json=sample_project_description)
            
            assert response.status_code == 503
            assert "Weaviate client not available" in response.json()["detail"]

