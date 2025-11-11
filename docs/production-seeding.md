# Production Database Seeding Guide

This guide explains how to add consultants to the production Weaviate database running on the remote VM.

## Prerequisites

- SSH access to the production server
- SSH key configured (`~/.ssh/clientGraph`)
- Access to the production VM: `ubuntu@35.159.37.114`
- Local development environment with Python virtual environment set up

## Overview

The production database uses Weaviate to store consultant data. There are several ways to add consultants:

1. **Generate new consultants** using the mock data generator
2. **Import from a JSON file** with custom consultant data
3. **Use the existing seeding script** that runs on container startup (controlled by `SEED_MOCK_DATA` env var)

## Method 1: Generate and Insert New Consultants (Recommended)

This method generates realistic consultant data using Faker and inserts it into the database.

### Step 1: Generate Consultants Locally

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python scripts/generate_mock_data.py --count 20 --output /tmp/new_consultants.json
```

**Options:**
- `--count N`: Number of consultants to generate (default: 30)
- `--output PATH`: Save to JSON file instead of inserting directly

### Step 2: Copy to Remote Server

```bash
scp -i ~/.ssh/clientGraph /tmp/new_consultants.json ubuntu@35.159.37.114:/tmp/new_consultants.json
```

### Step 3: Copy into Backend Container

```bash
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker cp /tmp/new_consultants.json projmatch-backend:/tmp/new_consultants.json"
```

### Step 4: Insert into Database

```bash
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker exec projmatch-backend python scripts/seed_production.py --data-file /tmp/new_consultants.json"
```

### Complete One-Liner

```bash
# Generate, copy, and insert in one go
cd backend && source venv/bin/activate && \
python scripts/generate_mock_data.py --count 20 --output /tmp/new_consultants.json && \
scp -i ~/.ssh/clientGraph /tmp/new_consultants.json ubuntu@35.159.37.114:/tmp/ && \
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker cp /tmp/new_consultants.json projmatch-backend:/tmp/ && docker exec projmatch-backend python scripts/seed_production.py --data-file /tmp/new_consultants.json"
```

## Method 2: Import from Custom JSON File

If you have a custom JSON file with consultant data, you can import it directly.

### JSON File Format

```json
[
  {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-0101",
    "skills": ["React", "TypeScript", "Node.js", "AWS"],
    "availability": "available",
    "experience": "8 years of full-stack development experience",
    "education": "BS in Computer Science from MIT"
  },
  {
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "phone": "+1-555-0102",
    "skills": ["Python", "Machine Learning", "TensorFlow"],
    "availability": "busy",
    "experience": "10 years in AI and data engineering",
    "education": "PhD in Machine Learning from Stanford"
  }
]
```

**Required Fields:**
- `name`: String - Consultant's full name
- `email`: String - Email address
- `phone`: String - Phone number
- `skills`: Array of strings - List of skills
- `availability`: String - One of: `"available"`, `"busy"`, or `"unavailable"`
- `experience`: String - Experience description
- `education`: String - Education details

### Import Steps

```bash
# 1. Copy your JSON file to remote server
scp -i ~/.ssh/clientGraph /path/to/your/consultants.json ubuntu@35.159.37.114:/tmp/consultants.json

# 2. Copy into backend container
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker cp /tmp/consultants.json projmatch-backend:/tmp/consultants.json"

# 3. Insert into database
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker exec projmatch-backend python scripts/seed_production.py --data-file /tmp/consultants.json"
```

## Method 3: Using stdin (Pipe JSON)

You can also pipe JSON data directly:

```bash
cat consultants.json | ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker exec -i projmatch-backend python scripts/seed_production.py --stdin"
```

## Verification

After inserting consultants, verify the insertion:

```bash
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker exec projmatch-backend python -c \"
import weaviate
import os
client = weaviate.Client(url=os.getenv('WEAVIATE_URL', 'http://weaviate:8080'))
result = client.query.get('Consultant', ['name', 'availability']).with_limit(100).do()
consultants = result.get('data', {}).get('Get', {}).get('Consultant', [])
print('Total consultants:', len(consultants))
\""
```

## Available Scripts

### `seed_production.py`

Production-ready seeding script with validation and error handling.

**Location:** `/app/scripts/seed_production.py` (inside container)

**Usage:**
```bash
docker exec projmatch-backend python scripts/seed_production.py --help
```

**Options:**
- `--data-file PATH`: Path to JSON file containing consultant data
- `--stdin`: Read consultant data from stdin (JSON array)
- `--force`: Insert consultants even if data already exists

**Features:**
- Validates consultant data structure
- Checks for existing consultants (unless `--force` is used)
- Batch inserts for efficiency
- Provides detailed progress and error reporting
- Verifies insertion after completion

### `generate_mock_data.py`

Generates realistic consultant data using Faker.

**Location:** `backend/scripts/generate_mock_data.py` (local)

**Usage:**
```bash
python scripts/generate_mock_data.py --count 20 --output consultants.json
```

**Options:**
- `--count N`: Number of consultants to generate (default: 30)
- `--output PATH`: Save to JSON file (if not provided, inserts directly)
- `--insert`: Insert generated data into Weaviate
- `--force`: Force re-seeding even if data exists

### `insert_mock_data.py`

Original seeding script (used by container startup).

**Location:** `/app/scripts/insert_mock_data.py` (inside container)

**Usage:**
```bash
docker exec projmatch-backend python scripts/insert_mock_data.py --data-file /path/to/data.json
```

## Container Startup Seeding

The production containers automatically seed data on startup if `SEED_MOCK_DATA=true` is set in the environment.

**Configuration:**
- Set in `docker-compose.prod.yml` or environment variables
- Controlled by `SEED_MOCK_DATA` environment variable
- Uses `insert_mock_data.py` script
- Reads from `backend/data/mock_consultants.json` (if available in container)

**To disable automatic seeding:**
```bash
# In docker-compose.prod.yml or environment
SEED_MOCK_DATA=false
```

**To force re-seeding on startup:**
```bash
FORCE_SEED=true SEED_MOCK_DATA=true
```

## Troubleshooting

### Connection Issues

If you can't connect to Weaviate:

```bash
# Check if containers are running
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "cd /opt/projmatch && docker compose -f docker-compose.prod.yml ps"

# Check Weaviate health
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker exec projmatch-weaviate wget --spider -q http://localhost:8080/v1/.well-known/ready && echo 'Weaviate is healthy'"
```

### Script Not Found

If the seeding script is not in the container:

```bash
# Copy script to container
scp -i ~/.ssh/clientGraph backend/scripts/seed_production.py ubuntu@35.159.37.114:/tmp/
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker cp /tmp/seed_production.py projmatch-backend:/app/scripts/seed_production.py"
```

### Validation Errors

If consultants fail validation, check:
- All required fields are present
- `skills` is an array
- `availability` is one of: `available`, `busy`, `unavailable`
- JSON is valid and properly formatted

### Existing Data

By default, the script will skip insertion if consultants already exist. To force insertion:

```bash
docker exec projmatch-backend python scripts/seed_production.py --data-file /tmp/consultants.json --force
```

## Best Practices

1. **Always verify** after inserting consultants
2. **Use batch operations** for large datasets (the script handles this automatically)
3. **Backup before major changes** (if needed, export existing data first)
4. **Test locally** before running in production
5. **Use descriptive JSON files** with meaningful names
6. **Clean up temporary files** after successful insertion

## Example Workflow

Complete example workflow for adding 50 new consultants:

```bash
# 1. Generate consultants locally
cd backend
source venv/bin/activate
python scripts/generate_mock_data.py --count 50 --output /tmp/prod_consultants_$(date +%Y%m%d).json

# 2. Review the generated data (optional)
cat /tmp/prod_consultants_*.json | jq '.[0]'  # Preview first consultant

# 3. Copy to production
scp -i ~/.ssh/clientGraph /tmp/prod_consultants_*.json ubuntu@35.159.37.114:/tmp/

# 4. Insert into database
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker cp /tmp/prod_consultants_*.json projmatch-backend:/tmp/ && docker exec projmatch-backend python scripts/seed_production.py --data-file /tmp/prod_consultants_*.json"

# 5. Verify
ssh -i ~/.ssh/clientGraph ubuntu@35.159.37.114 "docker exec projmatch-backend python -c \"import weaviate, os; c = weaviate.Client(url=os.getenv('WEAVIATE_URL', 'http://weaviate:8080')); r = c.query.get('Consultant', ['name']).with_limit(200).do(); print('Total:', len(r.get('data', {}).get('Get', {}).get('Consultant', [])))\""

# 6. Clean up
rm /tmp/prod_consultants_*.json
```

## Related Documentation

- [Main README](../README.md) - General project setup
- [Backend Setup](../backend/README.md) - Backend development guide
- [Docker Compose Production](../docker-compose.prod.yml) - Production configuration

## Support

For issues or questions:
1. Check container logs: `docker logs projmatch-backend`
2. Check Weaviate logs: `docker logs projmatch-weaviate`
3. Verify environment variables are set correctly
4. Ensure network connectivity between containers

