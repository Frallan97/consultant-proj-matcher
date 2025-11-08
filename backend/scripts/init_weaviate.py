"""
Initialize Weaviate schema for Consultant and Resume classes.
"""
import weaviate
import os
from dotenv import load_dotenv

load_dotenv()

# Default to weaviate service name for Docker Compose, fallback to localhost for local dev
weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080")

print(f"Connecting to Weaviate at {weaviate_url}")

# Wait for Weaviate to be ready (with retries)
import time
max_retries = 30
retry_delay = 2

for attempt in range(max_retries):
    try:
        client = weaviate.Client(url=weaviate_url)
        # Test connection
        client.schema.get()
        print("Successfully connected to Weaviate")
        break
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print(f"Failed to connect to Weaviate after {max_retries} attempts: {e}")
            raise

# Define the Consultant schema
consultant_schema = {
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

# Define the Resume schema
resume_schema = {
    "class": "Resume",
    "description": "A resume parsed from PDF",
    "properties": [
        {
            "name": "name",
            "dataType": ["string"],
            "description": "Name extracted from resume"
        },
        {
            "name": "email",
            "dataType": ["string"],
            "description": "Email address from resume"
        },
        {
            "name": "phone",
            "dataType": ["string"],
            "description": "Phone number from resume"
        },
        {
            "name": "skills",
            "dataType": ["string[]"],
            "description": "List of skills extracted from resume"
        },
        {
            "name": "experience",
            "dataType": ["text"],
            "description": "Work experience summary"
        },
        {
            "name": "education",
            "dataType": ["text"],
            "description": "Education details"
        },
        {
            "name": "full_text",
            "dataType": ["text"],
            "description": "Complete extracted text for vectorization"
        }
    ]
}

# Check if Consultant class exists, if so delete it
try:
    client.schema.delete_class("Consultant")
    print("Deleted existing Consultant class")
except:
    print("No existing Consultant class found")

# Create the Consultant class
try:
    client.schema.create_class(consultant_schema)
    print("Successfully created Consultant class in Weaviate")
except Exception as e:
    print(f"Error creating Consultant schema: {e}")

# Check if Resume class exists, if so delete it
try:
    client.schema.delete_class("Resume")
    print("Deleted existing Resume class")
except:
    print("No existing Resume class found")

# Create the Resume class
try:
    client.schema.create_class(resume_schema)
    print("Successfully created Resume class in Weaviate")
except Exception as e:
    print(f"Error creating Resume schema: {e}")

