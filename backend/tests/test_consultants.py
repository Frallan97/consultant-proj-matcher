"""
Tests for consultant CRUD operations.
"""
import pytest
import uuid


@pytest.mark.asyncio
async def test_get_all_consultants(clean_weaviate, test_app):
    """Test getting all consultants."""
    # Insert test consultants
    consultant1 = {
        "name": "Developer 1",
        "email": "dev1@example.com",
        "phone": "111-111-1111",
        "skills": ["Python"],
        "availability": "available",
        "experience": "5 years",
        "education": "BS"
    }
    
    consultant2 = {
        "name": "Developer 2",
        "email": "dev2@example.com",
        "phone": "222-222-2222",
        "skills": ["Java"],
        "availability": "available",
        "experience": "3 years",
        "education": "BS"
    }
    
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    
    clean_weaviate.data_object.create(data_object=consultant1, class_name="Consultant", uuid=id1)
    clean_weaviate.data_object.create(data_object=consultant2, class_name="Consultant", uuid=id2)
    
    async with test_app as client:
        response = await client.get("/api/consultants")
        
        assert response.status_code == 200
        data = response.json()
        assert "consultants" in data
        assert len(data["consultants"]) >= 2
        
        # Verify structure
        for consultant in data["consultants"]:
            assert "id" in consultant
            assert "name" in consultant
            assert "email" in consultant
            assert "resumeId" in consultant


@pytest.mark.asyncio
async def test_get_all_consultants_empty(clean_weaviate, test_app):
    """Test getting all consultants when database is empty."""
    async with test_app as client:
        response = await client.get("/api/consultants")
        
        assert response.status_code == 200
        data = response.json()
        assert data["consultants"] == []


@pytest.mark.asyncio
async def test_delete_consultant_success(clean_weaviate, test_app):
    """Test successful consultant deletion."""
    consultant = {
        "name": "Test Developer",
        "email": "test@example.com",
        "phone": "111-111-1111",
        "skills": ["Python"],
        "availability": "available",
        "experience": "5 years",
        "education": "BS"
    }
    
    consultant_id = str(uuid.uuid4())
    clean_weaviate.data_object.create(data_object=consultant, class_name="Consultant", uuid=consultant_id)
    
    async with test_app as client:
        response = await client.delete(f"/api/consultants/{consultant_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify consultant was deleted
        try:
            clean_weaviate.data_object.get_by_id(uuid=consultant_id, class_name="Consultant")
            assert False, "Consultant should have been deleted"
        except:
            pass  # Expected - consultant doesn't exist


@pytest.mark.asyncio
async def test_delete_consultant_not_found(test_app):
    """Test deleting non-existent consultant."""
    fake_id = str(uuid.uuid4())
    
    async with test_app as client:
        response = await client.delete(f"/api/consultants/{fake_id}")
        
        # Should still return success, but consultant doesn't exist
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_consultants_batch(clean_weaviate, test_app):
    """Test batch consultant deletion."""
    consultant1 = {
        "name": "Developer 1",
        "email": "dev1@example.com",
        "phone": "111-111-1111",
        "skills": ["Python"],
        "availability": "available",
        "experience": "5 years",
        "education": "BS"
    }
    
    consultant2 = {
        "name": "Developer 2",
        "email": "dev2@example.com",
        "phone": "222-222-2222",
        "skills": ["Java"],
        "availability": "available",
        "experience": "3 years",
        "education": "BS"
    }
    
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    
    clean_weaviate.data_object.create(data_object=consultant1, class_name="Consultant", uuid=id1)
    clean_weaviate.data_object.create(data_object=consultant2, class_name="Consultant", uuid=id2)
    
    async with test_app as client:
        response = await client.request("DELETE", "/api/consultants", json={"ids": [id1, id2]})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 2


@pytest.mark.asyncio
async def test_delete_consultants_batch_empty_ids(test_app):
    """Test batch deletion with empty IDs."""
    async with test_app as client:
        response = await client.request("DELETE", "/api/consultants", json={"ids": []})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No IDs provided" in data["error"]

