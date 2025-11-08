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
    "vectorizer": "text2vec-openai",
    "moduleConfig": {
        "text2vec-openai": {
            "model": "text-embedding-3-small",
            "type": "text"
        }
    },
    "properties": [
        {
            "name": "name",
            "dataType": ["string"],
            "description": "The name of the consultant",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizePropertyName": False
                }
            }
        },
        {
            "name": "email",
            "dataType": ["string"],
            "description": "Email address of the consultant",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizePropertyName": False
                }
            }
        },
        {
            "name": "phone",
            "dataType": ["string"],
            "description": "Phone number of the consultant",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizePropertyName": False
                }
            }
        },
        {
            "name": "skills",
            "dataType": ["string[]"],
            "description": "List of skills the consultant has",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizePropertyName": False
                }
            }
        },
        {
            "name": "availability",
            "dataType": ["string"],
            "description": "Availability status: available, busy, or unavailable",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizePropertyName": False
                }
            }
        },
        {
            "name": "experience",
            "dataType": ["text"],
            "description": "Experience description of the consultant",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizePropertyName": False
                }
            }
        },
        {
            "name": "education",
            "dataType": ["text"],
            "description": "Education details of the consultant",
            "moduleConfig": {
                "text2vec-openai": {
                    "vectorizePropertyName": False
                }
            }
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
        }
    ]
}

# Check if Consultant class exists
schema = client.schema.get()
class_names = [c["class"] for c in schema.get("classes", [])]

consultant_created = False
if "Consultant" in class_names:
    print("Consultant class already exists - preserving existing data")
    print("Note: If you need to update the schema (e.g., change embedding model), you'll need to manually migrate the data")
    consultant_created = True
else:
    # Create the Consultant class
    try:
        client.schema.create_class(consultant_schema)
        print("Successfully created Consultant class in Weaviate")
        consultant_created = True
    except Exception as e:
        print(f"Error creating Consultant schema: {e}")
        import sys
        sys.exit(1)

# Verify Consultant class exists (critical for application)
if not consultant_created:
    print("ERROR: Consultant class was not created and does not exist")
    import sys
    sys.exit(1)

# Verify Consultant class exists in schema
schema_after = client.schema.get()
class_names_after = [c["class"] for c in schema_after.get("classes", [])]
if "Consultant" not in class_names_after:
    print("ERROR: Consultant class verification failed - class does not exist in schema")
    import sys
    sys.exit(1)

# Check if Resume class exists
if "Resume" in class_names:
    print("Resume class already exists - preserving existing data")
else:
    # Create the Resume class
    try:
        client.schema.create_class(resume_schema)
        print("Successfully created Resume class in Weaviate")
    except Exception as e:
        print(f"Warning: Error creating Resume schema: {e}")
        # Resume schema is not critical, so we don't fail on this

print("Schema initialization completed successfully")

