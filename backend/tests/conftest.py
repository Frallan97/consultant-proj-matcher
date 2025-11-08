"""
Shared test fixtures and configuration.
"""
import os
import sys
import tempfile
import shutil
import time
import pytest
import weaviate
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from testcontainers.core.container import DockerContainer
from faker import Faker

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set default environment variables before importing main
# This ensures load_dotenv() in main.py has something to work with
if "OPENAI_APIKEY" not in os.environ:
    os.environ["OPENAI_APIKEY"] = "test-key-default"

from main import app
from storage import LocalFileStorage

fake = Faker()

# Weaviate schema definition
CONSULTANT_SCHEMA = {
    "class": "Consultant",
    "description": "A consultant with skills and availability",
    "vectorizer": "none",  # Use none for testing to avoid OpenAI dependency
    "properties": [
        {
            "name": "name",
            "dataType": ["string"],
            "description": "The name of the consultant"
        },
        {
            "name": "email",
            "dataType": ["string"],
            "description": "Email address of the consultant"
        },
        {
            "name": "phone",
            "dataType": ["string"],
            "description": "Phone number of the consultant"
        },
        {
            "name": "skills",
            "dataType": ["string[]"],
            "description": "List of skills the consultant has"
        },
        {
            "name": "availability",
            "dataType": ["string"],
            "description": "Availability status: available, busy, or unavailable"
        },
        {
            "name": "experience",
            "dataType": ["text"],
            "description": "Experience description of the consultant"
        },
        {
            "name": "education",
            "dataType": ["text"],
            "description": "Education details of the consultant"
        }
    ]
}


@pytest.fixture(scope="session")
def weaviate_container():
    """Start Weaviate container for testing."""
    import requests
    
    container = (
        DockerContainer("semitechnologies/weaviate:1.24.0")
        .with_env("QUERY_DEFAULTS_LIMIT", "25")
        .with_env("AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", "true")
        .with_env("PERSISTENCE_DATA_PATH", "/var/lib/weaviate")
        .with_env("DEFAULT_VECTORIZER_MODULE", "none")
        .with_env("ENABLE_MODULES", "text2vec-openai")
        .with_env("CLUSTER_HOSTNAME", "node1")
        .with_exposed_ports("8080")
    )
    
    with container:
        # Wait for Weaviate to be ready by checking HTTP endpoint
        host = container.get_container_host_ip()
        port = container.get_exposed_port("8080")
        url = f"http://{host}:{port}/v1/.well-known/ready"
        
        # Wait for HTTP endpoint to be ready with shorter timeout
        max_retries = 20
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise Exception(f"Failed to connect to Weaviate at {url} after {max_retries} attempts")
        
        time.sleep(1)  # Give it a moment to fully initialize
        
        yield container


@pytest.fixture(scope="session")
def weaviate_client(weaviate_container):
    """Create Weaviate client connected to test container."""
    host = weaviate_container.get_container_host_ip()
    port = weaviate_container.get_exposed_port("8080")
    url = f"http://{host}:{port}"
    
    # Wait for connection
    max_retries = 10
    for attempt in range(max_retries):
        try:
            client = weaviate.Client(url=url)
            client.schema.get()
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise Exception(f"Failed to connect to Weaviate: {e}")
    
    # Initialize schema
    schema = client.schema.get()
    class_names = [c["class"] for c in schema.get("classes", [])]
    
    if "Consultant" not in class_names:
        client.schema.create_class(CONSULTANT_SCHEMA)
    
    yield client
    
    # Cleanup: delete all consultants
    try:
        client.schema.delete_class("Consultant")
    except:
        pass


@pytest.fixture
def clean_weaviate(weaviate_client):
    """Clean Weaviate before each test and ensure schema exists."""
    # Ensure schema exists
    try:
        schema = weaviate_client.schema.get()
        class_names = [c["class"] for c in schema.get("classes", [])]
        if "Consultant" not in class_names:
            weaviate_client.schema.create_class(CONSULTANT_SCHEMA)
    except Exception:
        # If schema check fails, try to create it
        try:
            weaviate_client.schema.create_class(CONSULTANT_SCHEMA)
        except Exception:
            pass  # Schema might already exist
    
    # Delete all consultants - simplified and faster approach
    try:
        # Get all consultants in a single query (limit to reasonable number)
        result = weaviate_client.query.get("Consultant", ["name"]).with_limit(1000).with_additional(["id"]).do()
        
        if "data" in result and "Get" in result["data"] and "Consultant" in result["data"]["Get"]:
            consultants = result["data"]["Get"]["Consultant"]
            
            # Delete each consultant (batch delete would be better but this is simpler)
            for consultant in consultants:
                consultant_id = consultant.get("_additional", {}).get("id")
                if consultant_id:
                    try:
                        weaviate_client.data_object.delete(uuid=consultant_id, class_name="Consultant")
                    except:
                        pass
    except Exception:
        # If query fails, just continue - database might be empty or cleanup failed
        # This is not critical - tests should work even if cleanup fails
        pass
    
    yield weaviate_client


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_openai_resume_parser(monkeypatch):
    """Mock OpenAI for resume parsing."""
    # Set API key so the function doesn't fail on API key check
    monkeypatch.setenv("OPENAI_APIKEY", "test-key")
    
    # Patch os.getenv in the resume_parser module to ensure it picks up the test key
    # Import the module to get a reference to it (it may already be imported)
    import services.resume_parser as resume_parser_module
    import os as os_module
    
    # Store original getenv
    original_getenv = os_module.getenv
    
    def mock_getenv(key, default=None):
        if key == "OPENAI_APIKEY":
            return "test-key"
        return original_getenv(key, default)
    
    # Patch os.getenv in the resume_parser module's namespace
    monkeypatch.setattr(resume_parser_module.os, "getenv", mock_getenv)
    
    # Also patch the global os.getenv to be safe (in case it's used directly)
    # But we'll restore it after, so we only patch the module's os
    # The monkeypatch.setattr will automatically restore it after the test
    
    # Patch OpenAI class
    with patch('services.resume_parser.OpenAI') as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Default successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"name": "John Doe", "email": "john@example.com", "phone": "123-456-7890", "skills": ["Python", "FastAPI"], "experience": "5 years", "education": "BS Computer Science"}'
        mock_response.choices[0].finish_reason = "stop"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        yield mock_client


@pytest.fixture
def mock_openai_chat():
    """Mock OpenAI for chat endpoint."""
    with patch('services.chat_service.OpenAI') as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Default successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'Here are the roles:\n<roles>\n{"roles": [{"title": "Frontend Engineer", "description": "React developer", "query": "Frontend developer with React", "requiredSkills": ["React"]}]}\n</roles>'
        mock_response.choices[0].finish_reason = "stop"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        yield mock_client


@pytest.fixture
def test_app(weaviate_client, temp_storage_dir, monkeypatch):
    """Create test FastAPI app instance."""
    # Set environment variables
    host = weaviate_client._connection.url.replace("http://", "").replace("https://", "")
    monkeypatch.setenv("WEAVIATE_URL", f"http://{host}")
    monkeypatch.setenv("UPLOAD_DIR", temp_storage_dir)
    monkeypatch.setenv("OPENAI_APIKEY", "test-key")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    
    # Import here to avoid circular imports
    import main
    from services.consultant_service import ConsultantService
    from services.matching_service import MatchingService
    from services.overview_service import OverviewService
    
    # Patch the global client and storage in main.py
    original_client = main.client
    original_storage = main.storage
    original_consultant_service = main.consultant_service
    original_matching_service = main.matching_service
    original_overview_service = main.overview_service
    original_chat_service = main.chat_service
    
    main.client = weaviate_client
    main.storage = LocalFileStorage(base_dir=temp_storage_dir)
    
    # Reinitialize services with the new client
    main.consultant_service = ConsultantService(weaviate_client) if weaviate_client else None
    main.matching_service = MatchingService(weaviate_client, main.consultant_service, main.storage) if weaviate_client and main.consultant_service else None
    main.overview_service = OverviewService(main.consultant_service) if main.consultant_service else None
    main.chat_service = None  # Will be initialized lazily when needed
    
    from httpx import AsyncClient
    
    try:
        yield AsyncClient(app=app, base_url="http://test")
    finally:
        # Restore original client, storage, and services
        main.client = original_client
        main.storage = original_storage
        main.consultant_service = original_consultant_service
        main.matching_service = original_matching_service
        main.overview_service = original_overview_service
        main.chat_service = original_chat_service


@pytest.fixture
def sample_consultant_data():
    """Generate sample consultant data."""
    return {
        "name": fake.name(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "skills": ["Python", "FastAPI", "Docker"],
        "availability": "available",
        "experience": f"{fake.random_int(min=1, max=10)} years of software development",
        "education": "BS Computer Science"
    }


@pytest.fixture
def sample_pdf_bytes():
    """Generate minimal valid PDF bytes for testing."""
    # This is a minimal valid PDF
    pdf_content = b"""%PDF-1.4
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
    return pdf_content


@pytest.fixture
def sample_project_description():
    """Generate sample project description."""
    return {
        "projectDescription": "We need a Python developer with FastAPI experience for a web application project."
    }


@pytest.fixture
def sample_role_queries():
    """Generate sample role queries."""
    return {
        "roles": [
            {
                "title": "Frontend Engineer",
                "description": "React developer needed",
                "query": "Frontend developer with React and TypeScript",
                "requiredSkills": ["React", "TypeScript"]
            },
            {
                "title": "Backend Engineer",
                "description": "Python backend developer",
                "query": "Backend developer with Python and FastAPI",
                "requiredSkills": ["Python", "FastAPI"]
            }
        ]
    }

