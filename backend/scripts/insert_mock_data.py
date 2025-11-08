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
        "email": "sarah.johnson@example.com",
        "phone": "+1-555-0101",
        "skills": ["React", "TypeScript", "Node.js", "AWS"],
        "availability": "available",
        "experience": "8 years of full-stack development experience",
        "education": "BS in Computer Science from MIT",
    },
    {
        "name": "Michael Chen",
        "email": "michael.chen@example.com",
        "phone": "+1-555-0102",
        "skills": ["Python", "Machine Learning", "Data Science", "TensorFlow"],
        "availability": "available",
        "experience": "10 years in AI and data engineering",
        "education": "PhD in Machine Learning from Stanford",
    },
    {
        "name": "Emma Williams",
        "email": "emma.williams@example.com",
        "phone": "+1-555-0103",
        "skills": ["Java", "Spring Boot", "Microservices", "Kubernetes"],
        "availability": "busy",
        "experience": "7 years in enterprise software development",
        "education": "MS in Software Engineering from Carnegie Mellon",
    },
    {
        "name": "David Martinez",
        "email": "david.martinez@example.com",
        "phone": "+1-555-0104",
        "skills": ["React", "Vue.js", "GraphQL", "PostgreSQL"],
        "availability": "available",
        "experience": "6 years in frontend and backend development",
        "education": "BS in Computer Science from UC Berkeley",
    },
    {
        "name": "Lisa Anderson",
        "email": "lisa.anderson@example.com",
        "phone": "+1-555-0105",
        "skills": ["C#", ".NET", "Azure", "SQL Server"],
        "availability": "available",
        "experience": "9 years in Microsoft stack development",
        "education": "BS in Information Systems from University of Washington",
    },
    {
        "name": "James Wilson",
        "email": "james.wilson@example.com",
        "phone": "+1-555-0106",
        "skills": ["Go", "Docker", "Kubernetes", "CI/CD"],
        "availability": "unavailable",
        "experience": "5 years in DevOps and cloud infrastructure",
        "education": "BS in Computer Engineering from Georgia Tech",
    },
    {
        "name": "Maria Garcia",
        "email": "maria.garcia@example.com",
        "phone": "+1-555-0107",
        "skills": ["Python", "Django", "PostgreSQL", "REST APIs"],
        "availability": "available",
        "experience": "6 years in backend development",
        "education": "BS in Computer Science from UT Austin",
    },
    {
        "name": "Robert Brown",
        "email": "robert.brown@example.com",
        "phone": "+1-555-0108",
        "skills": ["JavaScript", "React", "Next.js", "TypeScript"],
        "availability": "available",
        "experience": "5 years in frontend development",
        "education": "BS in Web Development from Full Sail University",
    },
    {
        "name": "Jennifer Lee",
        "email": "jennifer.lee@example.com",
        "phone": "+1-555-0109",
        "skills": ["Swift", "iOS", "UIKit", "SwiftUI"],
        "availability": "busy",
        "experience": "7 years in mobile app development",
        "education": "BS in Mobile Computing from San Jose State",
    },
    {
        "name": "Thomas Anderson",
        "email": "thomas.anderson@example.com",
        "phone": "+1-555-0110",
        "skills": ["Kotlin", "Android", "Jetpack Compose", "Firebase"],
        "availability": "available",
        "experience": "6 years in Android development",
        "education": "BS in Software Engineering from Oregon State",
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
    
    # Check if database already has consultants
    try:
        result = client.query.get("Consultant", ["name"]).with_limit(1).do()
        existing_count = len(result.get("data", {}).get("Get", {}).get("Consultant", []))
        if existing_count > 0:
            print(f"Database already contains consultant(s). Skipping mock data insertion.")
            print("To force re-seeding, delete existing data first.")
            return
    except Exception as e:
        print(f"Warning: Could not check existing data: {e}")
        # Continue anyway
    
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

