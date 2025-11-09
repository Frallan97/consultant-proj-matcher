"""
Tests for chat endpoint.
"""
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_chat_endpoint_success(test_app, mock_openai_chat):
    """Test chat endpoint with successful response."""
    async with test_app as client:
        response = await client.post("/api/chat", json={
            "messages": [
                {"role": "user", "content": "I need a web app team"}
            ]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"
        assert "content" in data
        assert data["isComplete"] is True
        assert "roles" in data
        assert data["roles"] is not None


@pytest.mark.asyncio
async def test_chat_endpoint_missing_api_key(test_app, monkeypatch):
    """Test chat endpoint when OpenAI API key is missing."""
    import main
    from config import reset_settings
    
    # Reset settings and chat service to force re-initialization
    reset_settings()
    main.chat_service = None
    
    # Delete the API key from environment
    monkeypatch.delenv("OPENAI_APIKEY", raising=False)
    reset_settings()  # Reset again to pick up deleted env var
    
    async with test_app as client:
        response = await client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}]
        })
        
        assert response.status_code == 500
        assert "OPENAI_APIKEY" in response.json()["detail"] or "not available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_endpoint_openai_failure(test_app, mock_openai_chat):
    """Test chat endpoint when OpenAI API fails."""
    import main
    # Reset chat service to force re-initialization
    main.chat_service = None
    
    mock_openai_chat.chat.completions.create.side_effect = Exception("API error")
    
    async with test_app as client:
        response = await client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}]
        })
        
        assert response.status_code == 500
        assert "Error processing chat" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_endpoint_invalid_json_response(test_app, mock_openai_chat):
    """Test chat endpoint with invalid JSON in OpenAI response."""
    import main
    # Reset chat service to force re-initialization
    main.chat_service = None
    
    mock_openai_chat.chat.completions.create.return_value.choices[0].message.content = "Invalid JSON {"
    
    async with test_app as client:
        response = await client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}]
        })
        
        # Should still return 200, but without roles
        assert response.status_code == 200
        data = response.json()
        assert data["isComplete"] is False or data["roles"] is None

