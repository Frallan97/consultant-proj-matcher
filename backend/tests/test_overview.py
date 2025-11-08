"""
Tests for overview statistics endpoint.
"""
import pytest
import uuid


@pytest.mark.asyncio
async def test_get_overview(clean_weaviate, test_app):
    """Test getting overview statistics."""
    # Insert consultants with different skills
    consultant1 = {
        "name": "Developer 1",
        "email": "dev1@example.com",
        "phone": "111-111-1111",
        "skills": ["Python", "FastAPI"],
        "availability": "available",
        "experience": "5 years",
        "education": "BS"
    }
    
    consultant2 = {
        "name": "Developer 2",
        "email": "dev2@example.com",
        "phone": "222-222-2222",
        "skills": ["Python", "Docker"],
        "availability": "available",
        "experience": "3 years",
        "education": "BS"
    }
    
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    
    clean_weaviate.data_object.create(data_object=consultant1, class_name="Consultant", uuid=id1)
    clean_weaviate.data_object.create(data_object=consultant2, class_name="Consultant", uuid=id2)
    
    async with test_app as client:
        response = await client.get("/api/overview")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cvCount"] == 2
        assert data["uniqueSkillsCount"] >= 3  # Python, FastAPI, Docker
        assert len(data["topSkills"]) <= 10
        
        # Verify top skills structure
        for skill in data["topSkills"]:
            assert "skill" in skill
            assert "count" in skill
            assert skill["count"] > 0


@pytest.mark.asyncio
async def test_get_overview_empty(clean_weaviate, test_app):
    """Test overview with empty database."""
    async with test_app as client:
        response = await client.get("/api/overview")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cvCount"] == 0
        assert data["uniqueSkillsCount"] == 0
        assert data["topSkills"] == []

