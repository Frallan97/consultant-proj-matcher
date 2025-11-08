"""
Initialize Weaviate schema for Consultant class.
"""
import weaviate
import os
from dotenv import load_dotenv

load_dotenv()

weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")

client = weaviate.Client(url=weaviate_url)

# Define the schema
schema = {
    "class": "Consultant",
    "description": "A consultant with skills and availability",
    "properties": [
        {
            "name": "name",
            "dataType": ["string"],
            "description": "The name of the consultant"
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
            "dataType": ["string"],
            "description": "Experience description of the consultant"
        }
    ]
}

# Check if class exists, if so delete it
try:
    client.schema.delete_class("Consultant")
    print("Deleted existing Consultant class")
except:
    print("No existing Consultant class found")

# Create the class
try:
    client.schema.create_class(schema)
    print("Successfully created Consultant class in Weaviate")
except Exception as e:
    print(f"Error creating schema: {e}")

