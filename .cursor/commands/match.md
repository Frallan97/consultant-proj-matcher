# Running Tests

## Backend Tests

To run the backend tests, you need to activate the virtual environment first:

```bash
cd backend
source venv/bin/activate
pytest tests/ -v --tb=short
```

### Running specific test files:
```bash
pytest tests/test_main.py -v
pytest tests/test_upload.py -v
```

### Running performance tests:
```bash
# Run only performance tests
pytest tests/test_performance.py -v -m performance

# Run all tests except performance tests (faster)
pytest tests/ -v -m "not performance"

# Run all tests including performance
pytest tests/ -v
```

### Running with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

### Running tests in watch mode (if pytest-watch is installed):
```bash
ptw tests/
```

## Environment Setup

Before running tests, ensure:
1. Virtual environment is activated: `source backend/venv/bin/activate`
2. Dependencies are installed: `pip install -r backend/requirements.txt`
3. Test database (Weaviate) is available (tests use testcontainers)

## Test Configuration

Tests are configured in `backend/pytest.ini`:
- Async mode: auto
- Timeout: 300 seconds
- Test paths: `tests/`
- Performance tests are marked with `@pytest.mark.performance`

## Performance Test Thresholds

Performance tests verify response times:
- Health check: < 100ms
- Root endpoint: < 50ms
- Get all consultants: < 500ms
- Match consultants: < 1s
- Get overview: < 800ms
- Match roles: < 2s

