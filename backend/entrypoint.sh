#!/bin/bash
set -e

echo "Starting backend initialization..."

# Wait for Weaviate to be ready
echo "Waiting for Weaviate to be ready..."
WEAVIATE_URL=${WEAVIATE_URL:-http://weaviate:8080}
max_retries=30
retry_delay=2

for attempt in $(seq 1 $max_retries); do
  if curl -f -s "$WEAVIATE_URL/v1/.well-known/ready" > /dev/null 2>&1; then
    echo "Weaviate is ready!"
    break
  fi
  if [ $attempt -eq $max_retries ]; then
    echo "Warning: Weaviate not ready after $max_retries attempts, continuing anyway..."
  else
    echo "Waiting for Weaviate... (attempt $attempt/$max_retries)"
    sleep $retry_delay
  fi
done

# Initialize Weaviate schema
echo "Initializing Weaviate schema..."
if ! python scripts/init_weaviate.py; then
  echo "ERROR: Failed to initialize Weaviate schema. Exiting..."
  exit 1
fi
echo "Schema initialization successful"

# Seed mock data if SEED_MOCK_DATA is set to "true"
if [ "${SEED_MOCK_DATA:-false}" = "true" ]; then
  echo "Seeding mock data..."
  if python scripts/insert_mock_data.py; then
    echo "Mock data seeding successful"
  else
    echo "Warning: Failed to seed mock data, continuing anyway..."
  fi
fi

# Start the application
echo "Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2

