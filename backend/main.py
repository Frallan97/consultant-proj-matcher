from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import weaviate
import os
import uuid
from dotenv import load_dotenv
from storage import LocalFileStorage
from services.resume_parser import parse_resume_pdf
from services.consultant_service import ConsultantService
from services.matching_service import MatchingService
from services.chat_service import ChatService
from services.overview_service import OverviewService
from models import ConsultantData, ChatRequest, ChatResponse, ChatMessage, RoleQuery, RoleMatchRequest, RoleMatchResponse, RoleMatchResult

load_dotenv()

app = FastAPI(title="Consultant Matching API", version="1.0.0")

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8080")
cors_origins_list = [origin.strip() for origin in cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
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

# Initialize services
consultant_service = ConsultantService(client) if client else None
matching_service = MatchingService(client, consultant_service, storage) if client and consultant_service else None
chat_service = None  # Will be initialized lazily when needed
overview_service = OverviewService(consultant_service) if consultant_service else None

# Pydantic models
class Consultant(ConsultantData):
    id: Optional[str] = None
    matchScore: Optional[float] = None
    resumeId: Optional[str] = None  # If present, consultant has a resume PDF

class ProjectDescription(BaseModel):
    projectDescription: str

class ConsultantResponse(BaseModel):
    consultants: List[Consultant]

class DeleteRequest(BaseModel):
    ids: List[str]

class SkillCount(BaseModel):
    skill: str
    count: int

class OverviewResponse(BaseModel):
    cvCount: int
    uniqueSkillsCount: int
    topSkills: List[SkillCount]

@app.get("/")
async def root():
    return {"message": "Consultant Matching API"}

@app.get("/health")
async def health():
    """
    Health check endpoint that verifies database schema is initialized.
    Returns 503 if schema is not available.
    """
    if not client or not consultant_service:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "reason": "Weaviate client not available"}
        )
    
    if not consultant_service.schema_exists():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "reason": "Database schema not initialized"}
        )
    
    return {"status": "healthy", "database": "initialized"}

@app.post("/api/consultants/match", response_model=ConsultantResponse)
async def match_consultants(project: ProjectDescription):
    """
    Match consultants based on project description using Weaviate vector search.
    """
    if not matching_service:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    try:
        consultants = matching_service.match_consultants(project.projectDescription, limit=3)
        return ConsultantResponse(consultants=consultants)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        print(f"Error matching consultants: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error matching consultants: {error_msg}")

@app.get("/api/consultants", response_model=ConsultantResponse)
async def get_all_consultants():
    """
    Get all consultants.
    """
    if not consultant_service:
        return ConsultantResponse(consultants=[])
    
    try:
        consultants = consultant_service.get_all_consultants(limit=100)
        
        # Enrich with resume IDs
        for consultant in consultants:
            if consultant.get("id"):
                try:
                    pdf_path = storage.get_path(consultant["id"])
                    if os.path.exists(pdf_path):
                        consultant["resumeId"] = consultant["id"]
                except:
                    pass
        
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
    if not consultant_service:
        return {"success": False, "error": "Weaviate client not available"}
    
    try:
        success = consultant_service.delete_consultant(consultant_id)
        if success:
            return {"success": True, "message": f"Consultant {consultant_id} deleted successfully"}
        else:
            return {"success": False, "error": "Failed to delete consultant"}
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
    if not consultant_service:
        return {"success": False, "error": "Weaviate client not available"}
    
    if not request.ids:
        return {"success": False, "error": "No IDs provided"}
    
    try:
        deleted_count, errors = consultant_service.delete_consultants_batch(request.ids)
        
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
    if not consultant_service:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Generate UUID for consultant
    consultant_id = str(uuid.uuid4())
    
    try:
        # Read PDF bytes
        pdf_bytes = await file.read()
        
        # Parse resume - returns ConsultantData (pass bytes directly)
        consultant_data = parse_resume_pdf(pdf_bytes)
        
        # Save PDF to storage using consultant_id
        storage.save_pdf(pdf_bytes, consultant_id)
        
        # Insert into Weaviate Consultant collection with consultant_id as UUID
        consultant_service.create_consultant(consultant_data, consultant_id)
        
        # Return consultant object with ID and resumeId
        consultant_dict = consultant_data.model_dump()
        return {
            "id": consultant_id,
            **consultant_dict,
            "resumeId": consultant_id
        }
    
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
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF not found")
    except Exception as e:
        print(f"Error retrieving PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving PDF: {str(e)}")
@app.get("/api/overview", response_model=OverviewResponse)
async def get_overview():
    """
    Get overview statistics: number of CVs (consultants), unique skills, and top 10 most common skills.
    """
    if not overview_service:
        return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])
    
    return overview_service.get_overview()

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for interactive team assembly conversation.
    Uses OpenAI to ask clarifying questions and generate role queries.
    """
    global chat_service
    
    # Initialize chat service lazily
    if not chat_service:
        try:
            chat_service = ChatService()
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    try:
        return chat_service.process_chat(request.messages)
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.post("/api/consultants/match-roles", response_model=RoleMatchResponse)
async def match_consultants_by_roles(request: RoleMatchRequest):
    """
    Match consultants for multiple roles using vector search.
    Performs a separate vector search for each role query.
    """
    if not matching_service:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    try:
        role_results = []
        
        for role_query in request.roles:
            print(f"Searching for role '{role_query.title}' with query: '{role_query.query}'")
            
            try:
                consultants = matching_service.match_consultants_by_role(role_query.query, limit=3)
            except ValueError as e:
                # If no matches found, return empty list for this role
                print(f"No matches found for role '{role_query.title}': {e}")
                consultants = []
            
            # Ensure consultants is always a list, never None
            if consultants is None:
                consultants = []
            
            role_result = RoleMatchResult(
                role=role_query,
                consultants=consultants
            )
            print(f"Role '{role_query.title}': Found {len(consultants)} consultants")
            role_results.append(role_result)
        
        response_data = RoleMatchResponse(roles=role_results)
        print(f"Response has {len(response_data.roles)} roles")
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Check if it's a schema-related error
        if "no graphql provider" in error_msg.lower() or "no schema" in error_msg.lower():
            raise HTTPException(
                status_code=422,
                detail="No consultants found in database. Please upload consultant resumes first."
            )
        print(f"Error matching consultants by roles: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error matching consultants: {error_msg}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

