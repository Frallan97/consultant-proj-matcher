from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import weaviate
import os
import uuid
import tempfile
from dotenv import load_dotenv
from storage import LocalFileStorage
from services.resume_parser import parse_resume_pdf

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

# Storage
upload_dir = os.getenv("UPLOAD_DIR", "uploads/resumes")
storage = LocalFileStorage(base_dir=upload_dir)

# Pydantic models
class Consultant(BaseModel):
    id: Optional[str] = None
    name: str
    skills: List[str]
    availability: str
    experience: Optional[str] = None
    matchScore: Optional[float] = None
    hasResume: Optional[bool] = False
    resumeId: Optional[str] = None

class ProjectDescription(BaseModel):
    projectDescription: str

class ConsultantResponse(BaseModel):
    consultants: List[Consultant]

class DeleteRequest(BaseModel):
    ids: List[str]

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
        
        # Query Consultant collection
        response = (
            client.query
            .get("Consultant", ["name", "skills", "availability", "experience"])
            .with_additional(["id"])
            .with_limit(20)
            .do()
        )
        
        consultants = []
        if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
            results = response["data"]["Get"]["Consultant"]
            
            # Calculate match scores based on keyword matching
            for consultant in results:
                consultant_id = consultant.get("_additional", {}).get("id")
                match_score = calculate_match_score(consultant, query)
                consultants.append({
                    "id": consultant_id,
                    "name": consultant.get("name", ""),
                    "skills": consultant.get("skills", []),
                    "availability": consultant.get("availability", "unknown"),
                    "experience": consultant.get("experience"),
                    "matchScore": round(match_score, 1),
                    "hasResume": False,  # Will be determined by PDF existence
                    "resumeId": None
                })
                
                # Check if PDF exists for this consultant
                try:
                    pdf_path = storage.get_path(consultant_id)
                    if os.path.exists(pdf_path):
                        consultants[-1]["hasResume"] = True
                        consultants[-1]["resumeId"] = consultant_id
                except:
                    pass
            
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
            .with_additional(["id"])
            .with_limit(100)
            .do()
        )
        
        consultants = []
        if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
            results = response["data"]["Get"]["Consultant"]
            for consultant in results:
                # Extract ID from _additional field
                additional = consultant.get("_additional", {})
                consultant_id = additional.get("id")
                
                # Check if PDF exists for this consultant
                has_resume = False
                try:
                    pdf_path = storage.get_path(consultant_id)
                    has_resume = os.path.exists(pdf_path)
                except:
                    pass
                
                consultants.append({
                    "id": consultant_id,
                    "name": consultant.get("name", ""),
                    "skills": consultant.get("skills", []),
                    "availability": consultant.get("availability", "unknown"),
                    "experience": consultant.get("experience"),
                    "hasResume": has_resume,
                    "resumeId": consultant_id if has_resume else None
                })
        
        return ConsultantResponse(consultants=consultants)
    
    except Exception as e:
        print(f"Error fetching consultants: {e}")
        import traceback
        traceback.print_exc()
        return ConsultantResponse(consultants=[])

@app.delete("/api/consultants/{consultant_id}")
async def delete_consultant(consultant_id: str):
    """
    Delete a single consultant by ID.
    """
    if not client:
        return {"success": False, "error": "Weaviate client not available"}
    
    try:
        client.data_object.delete(
            uuid=consultant_id,
            class_name="Consultant"
        )
        return {"success": True, "message": f"Consultant {consultant_id} deleted successfully"}
    except Exception as e:
        print(f"Error deleting consultant {consultant_id}: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.delete("/api/consultants")
async def delete_consultants_batch(request: DeleteRequest):
    """
    Delete multiple consultants by IDs.
    """
    if not client:
        return {"success": False, "error": "Weaviate client not available"}
    
    if not request.ids:
        return {"success": False, "error": "No IDs provided"}
    
    try:
        deleted_count = 0
        errors = []
        
        for consultant_id in request.ids:
            try:
                client.data_object.delete(
                    uuid=consultant_id,
                    class_name="Consultant"
                )
                deleted_count += 1
            except Exception as e:
                errors.append({"id": consultant_id, "error": str(e)})
        
        if errors:
            return {
                "success": True,
                "message": f"Deleted {deleted_count} consultant(s), {len(errors)} error(s)",
                "deleted_count": deleted_count,
                "errors": errors
            }
        
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} consultant(s)",
            "deleted_count": deleted_count
        }
    except Exception as e:
        print(f"Error deleting consultants: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/api/resumes/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a PDF resume, parse it, and create a Consultant entry in Weaviate.
    Returns the consultant object with ID.
    """
    if not client:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Generate UUID for consultant
    consultant_id = str(uuid.uuid4())
    
    try:
        # Read PDF bytes
        pdf_bytes = await file.read()
        
        # Save PDF temporarily for parsing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Parse resume
            resume_data = parse_resume_pdf(tmp_path)
            
            # Save PDF to storage using consultant_id
            storage.save_pdf(pdf_bytes, consultant_id)
            
            # Create Consultant entry from parsed resume data
            consultant_data = {
                "name": resume_data.get("name", ""),
                "skills": resume_data.get("skills", []),
                "availability": "available",  # Default for uploaded resumes
                "experience": resume_data.get("experience", "")
            }
            
            # Insert into Weaviate Consultant collection with consultant_id as UUID
            client.data_object.create(
                data_object=consultant_data,
                class_name="Consultant",
                uuid=consultant_id
            )
            
            # Return consultant object with ID
            return {
                "id": consultant_id,
                **consultant_data,
                "hasResume": True,
                "resumeId": consultant_id
            }
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        # Clean up PDF if Weaviate insertion failed
        try:
            pdf_path = storage.get_path(consultant_id)
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except:
            pass
        
        print(f"Error uploading resume: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")

@app.get("/api/resumes/{resume_id}/pdf")
async def get_resume_pdf(resume_id: str):
    """
    Retrieve the original PDF file by consultant/resume ID.
    The ID is the same as the consultant ID for uploaded resumes.
    """
    try:
        file_path = storage.get_path(resume_id)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="PDF not found")
        
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=f"{resume_id}.pdf"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF not found")
    except Exception as e:
        print(f"Error retrieving PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

