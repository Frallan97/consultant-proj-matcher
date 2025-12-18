# Consultant Matching Web App

AI-powered web application for matching consultants to projects using semantic similarity search with Weaviate and OpenAI embeddings.

## Features

- **AI Chat Interface**: Interactive conversation to assemble teams and identify required roles
- **Vector Search Matching**: Semantic similarity matching using Weaviate and OpenAI embeddings
- **Resume Management**: Upload and manage consultant resumes via admin interface
- **Match Scoring**: Normalized match scores showing consultant relevance

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key

### Setup

1. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Add your OPENAI_APIKEY to .env
   ```

2. **Start services:**
   ```bash
   docker-compose up -d
   ```

3. **Initialize Weaviate schema:**
   ```bash
   docker-compose exec backend bash scripts/setup.sh
   ```

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - Weaviate: http://localhost:8080

## Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
bun install
bun run dev
```

**Run Tests:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate

# Run all tests (excluding performance tests)
pytest tests/ -v -m "not performance"

# Run only performance tests
pytest tests/test_performance.py -v -m performance

# Run all tests including performance
pytest tests/ -v

# Run specific test file
pytest tests/test_dependencies.py -v
```

## CI/CD

The project uses GitHub Actions for CI/CD:
- **Test job**: Runs unit and integration tests
- **Performance job**: Runs performance tests to ensure API response times meet thresholds
- **Lint job**: Checks code quality and formatting
- **Build and Push**: Builds Docker images and pushes to GitHub Container Registry (GHCR)

Tests run automatically on push and pull requests to `main` and `develop` branches.

## Kubernetes Deployment

The application is deployed to Kubernetes using ArgoCD and Helm.

**Live Application:** https://consultant-matcher.w.vibeoholic.com
**API Documentation:** https://consultant-matcher.w.vibeoholic.com/docs

### Deployment Details

- **Repository:** https://github.com/Frallan97/consultant-proj-matcher
- **Namespace:** consultant-matcher
- **Components:**
  - Frontend: React SPA served by Nginx
  - Backend: Python FastAPI application
  - Weaviate: Vector database for semantic search
- **Ingress:** Traefik with automatic TLS via cert-manager
- **Container Registry:** ghcr.io/frallan97/consultant-proj-matcher-*

### Helm Chart

The Helm chart is located in `charts/consultant-matcher/`. See the chart README for installation instructions.

### Managing the Deployment

```bash
# View pod status
kubectl get pods -n consultant-matcher

# View logs
kubectl logs -n consultant-matcher -l component=backend
kubectl logs -n consultant-matcher -l component=frontend
kubectl logs -n consultant-matcher -l component=weaviate

# Check ingress
kubectl get ingress -n consultant-matcher

# ArgoCD status
kubectl get application consultant-matcher -n argocd
```

### Performance Tests

Performance tests verify that API endpoints meet response time thresholds:
- Health check: < 100ms
- Root endpoint: < 50ms
- Get all consultants: < 500ms
- Match consultants: < 1s
- Get overview: < 800ms
- Match roles: < 2s

Tests also verify concurrent request handling and throughput.
