"""
Tests for health check endpoint.
"""
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_root_endpoint(test_app):
    """Test root endpoint."""
    async with test_app as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_health_check_healthy(clean_weaviate, test_app):
    """Test health check when Weaviate is connected and schema exists."""
    async with test_app as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "initialized"


@pytest.mark.asyncio
async def test_health_check_no_weaviate(test_app, monkeypatch):
    """Test health check when Weaviate client is unavailable."""
    import main
    with patch('main.client', None):
        # Also set consultant_service to None to ensure it's not cached
        main.consultant_service = None
        async with test_app as client:
            response = await client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "Weaviate client not available" in data["reason"]


@pytest.mark.asyncio
async def test_health_check_no_schema(clean_weaviate, test_app, monkeypatch):
    """Test health check when schema is not initialized."""
    # Delete the Consultant class
    clean_weaviate.schema.delete_class("Consultant")
    
    async with test_app as client:
        response = await client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Database schema not initialized" in data["reason"]

