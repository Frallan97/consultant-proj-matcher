"""
Insert mock consultant data into Weaviate.
"""
import weaviate
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import from main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        # Test connection by checking schema
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

# Mock consultant data
mock_consultants = [
    {
        "name": "Sarah Johnson",
        "skills": ["React", "TypeScript", "Node.js", "AWS"],
        "availability": "available",
        "experience": "8 years of full-stack development experience",
    },
    {
        "name": "Michael Chen",
        "skills": ["Python", "Machine Learning", "Data Science", "TensorFlow"],
        "availability": "available",
        "experience": "10 years in AI and data engineering",
    },
    {
        "name": "Emma Williams",
        "skills": ["Java", "Spring Boot", "Microservices", "Kubernetes"],
        "availability": "busy",
        "experience": "7 years in enterprise software development",
    },
    {
        "name": "David Martinez",
        "skills": ["React", "Vue.js", "GraphQL", "PostgreSQL"],
        "availability": "available",
        "experience": "6 years in frontend and backend development",
    },
    {
        "name": "Lisa Anderson",
        "skills": ["C#", ".NET", "Azure", "SQL Server"],
        "availability": "available",
        "experience": "9 years in Microsoft stack development",
    },
    {
        "name": "James Wilson",
        "skills": ["Go", "Docker", "Kubernetes", "CI/CD"],
        "availability": "unavailable",
        "experience": "5 years in DevOps and cloud infrastructure",
    },
    {
        "name": "Maria Garcia",
        "skills": ["Python", "Django", "PostgreSQL", "REST APIs"],
        "availability": "available",
        "experience": "6 years in backend development",
    },
    {
        "name": "Robert Brown",
        "skills": ["JavaScript", "React", "Next.js", "TypeScript"],
        "availability": "available",
        "experience": "5 years in frontend development",
    },
    {
        "name": "Jennifer Lee",
        "skills": ["Swift", "iOS", "UIKit", "SwiftUI"],
        "availability": "busy",
        "experience": "7 years in mobile app development",
    },
    {
        "name": "Thomas Anderson",
        "skills": ["Kotlin", "Android", "Jetpack Compose", "Firebase"],
        "availability": "available",
        "experience": "6 years in Android development",
    },
]

def insert_consultants():
    """Insert mock consultants into Weaviate."""
    # Check if class exists
    try:
        schema = client.schema.get()
        class_names = [c["class"] for c in schema.get("classes", [])]
        if "Consultant" not in class_names:
            print("Error: Consultant class does not exist. Please run init_weaviate.py first.")
            return
    except Exception as e:
        print(f"Error checking schema: {e}")
        return
    
    # Batch insert
    with client.batch as batch:
        batch.batch_size = 10
        batch.num_workers = 1
        
        for consultant in mock_consultants:
            try:
                batch.add_data_object(
                    data_object=consultant,
                    class_name="Consultant"
                )
                print(f"Added consultant: {consultant['name']}")
            except Exception as e:
                print(f"Error adding consultant {consultant['name']}: {e}")
    
    print(f"\nSuccessfully inserted {len(mock_consultants)} consultants into Weaviate")

if __name__ == "__main__":
    insert_consultants()

