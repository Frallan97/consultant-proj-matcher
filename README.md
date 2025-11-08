# Consultant Matching Web App

A web application for consulting firm managers to find matching consultants for their projects using FastAPI, Weaviate vector database, and React.

## Architecture

- **Frontend**: React with TypeScript, Tailwind CSS, and shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: Weaviate vector database
- **Deployment**: Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose
- (Optional) Bun for local frontend development

### Running with Docker Compose

1. Start all services:
```bash
docker-compose up -d
```

2. Initialize Weaviate schema and insert mock data:
```bash
docker-compose exec backend python scripts/init_weaviate.py
docker-compose exec backend python scripts/insert_mock_data.py
```

Or run the setup script:
```bash
docker-compose exec backend bash scripts/setup.sh
```

3. Access the application:
   - Frontend: http://localhost:8080 (if configured) or run locally with `bun run dev`
   - Backend API: http://localhost:8000
   - Weaviate: http://localhost:8080

### Local Development

#### Backend

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Weaviate URL
```

4. Initialize Weaviate (make sure Weaviate is running):
```bash
python scripts/init_weaviate.py
python scripts/insert_mock_data.py
```

5. Run the backend:
```bash
uvicorn main:app --reload
```

#### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
bun install
```

3. Run the development server:
```bash
bun run dev
```

## API Endpoints

- `GET /` - API root
- `GET /health` - Health check
- `POST /api/consultants/match` - Match consultants based on project description
  - Request body: `{ "projectDescription": "..." }`
  - Response: `{ "consultants": [...] }`
- `GET /api/consultants` - Get all consultants

## Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Backend Docker image
│   ├── scripts/
│   │   ├── init_weaviate.py # Initialize Weaviate schema
│   │   └── insert_mock_data.py # Insert mock consultant data
│   └── .env.example         # Environment variables template
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── ProjectDescriptionPage.tsx
│       │   └── ConsultantResultsPage.tsx
│       └── types/
│           └── consultant.ts
└── docker-compose.yml       # Docker Compose configuration
```

## Features

- Project description input with character limit
- Real-time consultant matching based on project requirements
- Consultant cards displaying skills, availability, and match scores
- Responsive design for mobile, tablet, and desktop
- Loading states and error handling

## Development Notes

- The backend uses simple keyword matching for now. In production, you would use vector embeddings for semantic search.
- Mock data includes 10 consultants with various skills and availability statuses.
- The frontend fetches data from the backend API when a project description is submitted.

