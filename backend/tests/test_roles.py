"""
Tests for role-based matching endpoint.
"""
import pytest
import uuid
import time


@pytest.mark.asyncio
async def test_match_consultants_by_roles(clean_weaviate, test_app, sample_role_queries):
    """Test matching consultants by roles."""
    # Insert test consultants
    consultant1 = {
        "name": "Frontend Developer",
        "email": "frontend@example.com",
        "phone": "111-111-1111",
        "skills": ["React", "TypeScript"],
        "availability": "available",
        "experience": "5 years frontend",
        "education": "BS"
    }
    
    consultant2 = {
        "name": "Backend Developer",
        "email": "backend@example.com",
        "phone": "222-222-2222",
        "skills": ["Python", "FastAPI"],
        "availability": "available",
        "experience": "5 years backend",
        "education": "BS"
    }
    
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    
    clean_weaviate.data_object.create(data_object=consultant1, class_name="Consultant", uuid=id1)
    clean_weaviate.data_object.create(data_object=consultant2, class_name="Consultant", uuid=id2)
    
    time.sleep(1)
    
    async with test_app as client:
        response = await client.post("/api/consultants/match-roles", json=sample_role_queries)
        
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert len(data["roles"]) == 2
        
        for role_result in data["roles"]:
            assert "role" in role_result
            assert "consultants" in role_result
            assert len(role_result["consultants"]) <= 3
            
            for consultant in role_result["consultants"]:
                assert "matchScore" in consultant
                assert 0 <= consultant["matchScore"] <= 100


@pytest.mark.asyncio
async def test_match_consultants_by_roles_empty_database(clean_weaviate, test_app, sample_role_queries):
    """Test matching by roles when database is empty (no consultants but schema exists)."""
    async with test_app as client:
        response = await client.post("/api/consultants/match-roles", json=sample_role_queries)
        
        # When schema exists but no consultants, returns 200 with empty results
        # (422 is only raised when schema doesn't exist)
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        # Each role should have empty consultants list
        for role_result in data["roles"]:
            assert "consultants" in role_result
            assert role_result["consultants"] == []

