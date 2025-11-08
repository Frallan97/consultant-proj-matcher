#!/bin/bash
# Setup script to initialize Weaviate and insert mock data

echo "Setting up Weaviate schema..."
python scripts/init_weaviate.py

echo "Inserting mock data..."
python scripts/insert_mock_data.py

echo "Setup complete!"

