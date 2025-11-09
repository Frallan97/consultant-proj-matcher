"""
Performance tests for API endpoints.
Tests response times, throughput, and concurrent request handling.
"""
import pytest
import asyncio
import time
import json
import uuid
from httpx import AsyncClient
from typing import List


# Performance thresholds (in seconds)
PERFORMANCE_THRESHOLDS = {
    "health_check": 0.1,  # 100ms
    "root_endpoint": 0.05,  # 50ms
    "get_all_consultants": 0.5,  # 500ms
    "match_consultants": 1.0,  # 1s
    "get_overview": 0.8,  # 800ms
    "match_roles": 2.0,  # 2s
}


@pytest.mark.asyncio
@pytest.mark.performance
async def test_health_check_performance(clean_weaviate, test_app):
    """Test health check endpoint performance."""
    async with test_app as client:
        start_time = time.time()
        response = await client.get("/health")
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < PERFORMANCE_THRESHOLDS["health_check"], \
            f"Health check took {elapsed_time:.3f}s, expected < {PERFORMANCE_THRESHOLDS['health_check']}s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_root_endpoint_performance(test_app):
    """Test root endpoint performance."""
    async with test_app as client:
        start_time = time.time()
        response = await client.get("/")
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < PERFORMANCE_THRESHOLDS["root_endpoint"], \
            f"Root endpoint took {elapsed_time:.3f}s, expected < {PERFORMANCE_THRESHOLDS['root_endpoint']}s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_get_all_consultants_performance(clean_weaviate, test_app, sample_consultant_data):
    """Test get all consultants endpoint performance."""
    # Create some test consultants
    import main
    from services.consultant_service import ConsultantService
    from models import ConsultantData
    
    consultant_service = ConsultantService(clean_weaviate)
    for i in range(10):
        consultant_data = ConsultantData(**sample_consultant_data)
        consultant_id = str(uuid.uuid4())
        await consultant_service.create_consultant(consultant_data, consultant_id)
    
    async with test_app as client:
        start_time = time.time()
        response = await client.get("/api/consultants")
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < PERFORMANCE_THRESHOLDS["get_all_consultants"], \
            f"Get all consultants took {elapsed_time:.3f}s, expected < {PERFORMANCE_THRESHOLDS['get_all_consultants']}s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_match_consultants_performance(clean_weaviate, test_app, sample_consultant_data, sample_project_description):
    """Test match consultants endpoint performance."""
    # Create some test consultants
    import main
    from services.consultant_service import ConsultantService
    from models import ConsultantData
    
    consultant_service = ConsultantService(clean_weaviate)
    for i in range(10):
        consultant_data = ConsultantData(**sample_consultant_data)
        consultant_id = str(uuid.uuid4())
        await consultant_service.create_consultant(consultant_data, consultant_id)
    
    async with test_app as client:
        start_time = time.time()
        response = await client.post(
            "/api/consultants/match",
            json=sample_project_description
        )
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < PERFORMANCE_THRESHOLDS["match_consultants"], \
            f"Match consultants took {elapsed_time:.3f}s, expected < {PERFORMANCE_THRESHOLDS['match_consultants']}s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_get_overview_performance(clean_weaviate, test_app, sample_consultant_data):
    """Test overview endpoint performance."""
    # Create some test consultants
    import main
    from services.consultant_service import ConsultantService
    from models import ConsultantData
    
    consultant_service = ConsultantService(clean_weaviate)
    for i in range(20):
        consultant_data = ConsultantData(**sample_consultant_data)
        consultant_id = str(uuid.uuid4())
        await consultant_service.create_consultant(consultant_data, consultant_id)
    
    async with test_app as client:
        start_time = time.time()
        response = await client.get("/api/overview")
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < PERFORMANCE_THRESHOLDS["get_overview"], \
            f"Get overview took {elapsed_time:.3f}s, expected < {PERFORMANCE_THRESHOLDS['get_overview']}s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_health_checks(clean_weaviate, test_app):
    """Test concurrent health check requests."""
    async with test_app as client:
        async def make_request():
            response = await client.get("/health")
            return response.status_code
        
        start_time = time.time()
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time
        
        assert all(status == 200 for status in results)
        # All 10 requests should complete in reasonable time
        assert elapsed_time < 1.0, \
            f"10 concurrent health checks took {elapsed_time:.3f}s, expected < 1.0s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_get_consultants(clean_weaviate, test_app, sample_consultant_data):
    """Test concurrent get consultants requests."""
    # Create some test consultants
    import main
    from services.consultant_service import ConsultantService
    from models import ConsultantData
    
    consultant_service = ConsultantService(clean_weaviate)
    for i in range(10):
        consultant_data = ConsultantData(**sample_consultant_data)
        consultant_id = str(uuid.uuid4())
        await consultant_service.create_consultant(consultant_data, consultant_id)
    
    async with test_app as client:
        async def make_request():
            response = await client.get("/api/consultants")
            return response.status_code
        
        start_time = time.time()
        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time
        
        assert all(status == 200 for status in results)
        # All 5 requests should complete in reasonable time
        assert elapsed_time < 2.0, \
            f"5 concurrent get consultants took {elapsed_time:.3f}s, expected < 2.0s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_match_roles_performance(clean_weaviate, test_app, sample_consultant_data, sample_role_queries):
    """Test match roles endpoint performance."""
    # Create some test consultants
    import main
    from services.consultant_service import ConsultantService
    from models import ConsultantData
    
    consultant_service = ConsultantService(clean_weaviate)
    for i in range(15):
        consultant_data = ConsultantData(**sample_consultant_data)
        consultant_id = str(uuid.uuid4())
        await consultant_service.create_consultant(consultant_data, consultant_id)
    
    async with test_app as client:
        start_time = time.time()
        response = await client.post(
            "/api/consultants/match-roles",
            json=sample_role_queries
        )
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < PERFORMANCE_THRESHOLDS["match_roles"], \
            f"Match roles took {elapsed_time:.3f}s, expected < {PERFORMANCE_THRESHOLDS['match_roles']}s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_throughput_health_endpoint(clean_weaviate, test_app):
    """Test throughput of health endpoint (requests per second)."""
    async with test_app as client:
        num_requests = 50
        start_time = time.time()
        
        tasks = [client.get("/health") for _ in range(num_requests)]
        responses = await asyncio.gather(*tasks)
        
        elapsed_time = time.time() - start_time
        requests_per_second = num_requests / elapsed_time
        
        assert all(r.status_code == 200 for r in responses)
        # Should handle at least 20 requests per second
        assert requests_per_second >= 20, \
            f"Throughput: {requests_per_second:.2f} req/s, expected >= 20 req/s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_response_time_percentiles(clean_weaviate, test_app):
    """Test response time percentiles for health endpoint."""
    async with test_app as client:
        response_times: List[float] = []
        num_requests = 100
        
        for _ in range(num_requests):
            start_time = time.time()
            await client.get("/health")
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)
        
        response_times.sort()
        p50 = response_times[int(num_requests * 0.5)]
        p95 = response_times[int(num_requests * 0.95)]
        p99 = response_times[int(num_requests * 0.99)]
        
        # P50 should be very fast
        assert p50 < 0.05, f"P50 response time: {p50:.3f}s, expected < 0.05s"
        # P95 should still be reasonable
        assert p95 < 0.2, f"P95 response time: {p95:.3f}s, expected < 0.2s"
        # P99 should be acceptable
        assert p99 < 0.5, f"P99 response time: {p99:.3f}s, expected < 0.5s"

