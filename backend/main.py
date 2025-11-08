from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import weaviate
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Consultant Matching API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Weaviate client
weaviate_url = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
try:
    client = weaviate.Client(url=weaviate_url)
except Exception as e:
    print(f"Warning: Could not connect to Weaviate at {weaviate_url}: {e}")
    client = None

# Pydantic models
class Consultant(BaseModel):
    id: Optional[str] = None
    name: str
    skills: List[str]
    availability: str
    experience: Optional[str] = None
    matchScore: Optional[float] = None

class ProjectDescription(BaseModel):
    projectDescription: str

class ConsultantResponse(BaseModel):
    consultants: List[Consultant]

@app.get("/")
async def root():
    return {"message": "Consultant Matching API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/consultants/match", response_model=ConsultantResponse)
async def match_consultants(project: ProjectDescription):
    """
    Match consultants based on project description using vector search.
    """
    if not client:
        return ConsultantResponse(consultants=[])
    
    try:
        # For now, we'll do a simple text search
        # In a real implementation, you'd use vector embeddings for semantic search
        query = project.projectDescription.lower()
        
        # Simple keyword matching - in production, use vector search
        response = (
            client.query
            .get("Consultant", ["name", "skills", "availability", "experience"])
            .with_limit(20)
            .do()
        )
        
        consultants = []
        if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
            results = response["data"]["Get"]["Consultant"]
            
            # Calculate match scores based on keyword matching
            for idx, consultant in enumerate(results):
                match_score = calculate_match_score(consultant, query)
                consultants.append({
                    "id": consultant.get("_additional", {}).get("id"),
                    "name": consultant.get("name", ""),
                    "skills": consultant.get("skills", []),
                    "availability": consultant.get("availability", "unknown"),
                    "experience": consultant.get("experience"),
                    "matchScore": round(match_score, 1)
                })
            
            # Sort by match score
            consultants.sort(key=lambda x: x["matchScore"] or 0, reverse=True)
        
        return ConsultantResponse(consultants=consultants)
    
    except Exception as e:
        print(f"Error matching consultants: {e}")
        import traceback
        traceback.print_exc()
        return ConsultantResponse(consultants=[])

def calculate_match_score(consultant: dict, query: str) -> float:
    """
    Calculate a simple match score based on keyword matching.
    In production, this would use vector similarity.
    """
    score = 0.0
    query_words = set(query.split())
    
    # Match skills
    skills = [s.lower() for s in consultant.get("skills", [])]
    for skill in skills:
        if any(word in skill for word in query_words):
            score += 10
    
    # Match experience
    experience = consultant.get("experience", "").lower()
    if experience:
        matches = sum(1 for word in query_words if word in experience)
        score += matches * 2
    
    # Normalize to 0-100
    return min(100.0, score)

@app.get("/api/consultants", response_model=ConsultantResponse)
async def get_all_consultants():
    """
    Get all consultants.
    """
    if not client:
        return ConsultantResponse(consultants=[])
    
    try:
        response = (
            client.query
            .get("Consultant", ["name", "skills", "availability", "experience"])
            .with_limit(100)
            .do()
        )
        
        consultants = []
        if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
            results = response["data"]["Get"]["Consultant"]
            for consultant in results:
                consultants.append({
                    "id": consultant.get("_additional", {}).get("id"),
                    "name": consultant.get("name", ""),
                    "skills": consultant.get("skills", []),
                    "availability": consultant.get("availability", "unknown"),
                    "experience": consultant.get("experience"),
                })
        
        return ConsultantResponse(consultants=consultants)
    
    except Exception as e:
        print(f"Error fetching consultants: {e}")
        import traceback
        traceback.print_exc()
        return ConsultantResponse(consultants=[])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

