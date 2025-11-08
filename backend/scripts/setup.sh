#!/bin/bash
# Setup script to initialize Weaviate and insert mock data

# If running inside Docker Compose, use the service name
# Otherwise, use the environment variable or default to localhost
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    # Running inside Docker - use service name
    export WEAVIATE_URL=${WEAVIATE_URL:-http://weaviate:8080}
    # Override if it's set to localhost (from .env file)
    if [ "$WEAVIATE_URL" = "http://localhost:8080" ]; then
        export WEAVIATE_URL=http://weaviate:8080
    fi
else
    # Running locally - use localhost
    export WEAVIATE_URL=${WEAVIATE_URL:-http://localhost:8080}
fi

echo "Setting up Weaviate schema..."
echo "Using Weaviate URL: $WEAVIATE_URL"
python scripts/init_weaviate.py

echo "Inserting mock data..."
python scripts/insert_mock_data.py

echo "Setup complete!"

