from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import weaviate
import os
import uuid
import logging
from dotenv import load_dotenv
from storage import LocalFileStorage
from services.resume_parser import parse_resume_pdf
from services.consultant_service import ConsultantService
from services.matching_service import MatchingService
from services.chat_service import ChatService
from services.overview_service import OverviewService
from models import ConsultantData, ChatRequest, ChatResponse, ChatMessage, RoleQuery, RoleMatchRequest, RoleMatchResponse, RoleMatchResult
from logger_config import setup_logging, get_logger

load_dotenv()

# Set up logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

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
    logger.info(f"Successfully connected to Weaviate at {weaviate_url}")
except (weaviate.exceptions.WeaviateBaseError, ConnectionError, Exception) as e:
    logger.warning(f"Could not connect to Weaviate at {weaviate_url}: {e}", exc_info=True)
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
async def root() -> Dict[str, str]:
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
async def match_consultants(project: ProjectDescription) -> ConsultantResponse:
    """
    Match consultants based on project description using Weaviate vector search.
    """
    if not matching_service:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    try:
        consultants = matching_service.match_consultants(project.projectDescription, limit=3)
        logger.info(f"Matched {len(consultants)} consultants for project description")
        return ConsultantResponse(consultants=consultants)
    except ValueError as e:
        logger.warning(f"Validation error matching consultants: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Error matching consultants", exc_info=True, extra={"endpoint": "/api/consultants/match"})
        error_msg = str(e)
        raise HTTPException(status_code=500, detail="Error matching consultants. Please try again later.")

@app.get("/api/consultants", response_model=ConsultantResponse)
async def get_all_consultants() -> ConsultantResponse:
    """
    Get all consultants.
    """
    if not consultant_service:
        logger.warning("Consultant service not available")
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
                except (OSError, ValueError) as e:
                    logger.debug(f"Could not check resume for consultant {consultant.get('id')}: {e}")
        
        logger.info(f"Retrieved {len(consultants)} consultants")
        return ConsultantResponse(consultants=consultants)
    except Exception as e:
        logger.error("Error fetching consultants", exc_info=True, extra={"endpoint": "/api/consultants"})
        return ConsultantResponse(consultants=[])

@app.delete("/api/consultants/{consultant_id}")
async def delete_consultant(consultant_id: str) -> Dict[str, Any]:
    """
    Delete a single consultant by ID.
    """
    if not consultant_service:
        return {"success": False, "error": "Weaviate client not available"}
    
    try:
        success = consultant_service.delete_consultant(consultant_id)
        if success:
            logger.info(f"Successfully deleted consultant {consultant_id}")
            return {"success": True, "message": f"Consultant {consultant_id} deleted successfully"}
        else:
            logger.warning(f"Failed to delete consultant {consultant_id}")
            return {"success": False, "error": "Failed to delete consultant"}
    except Exception as e:
        logger.error(f"Error deleting consultant {consultant_id}", exc_info=True, extra={"consultant_id": consultant_id})
        return {"success": False, "error": "Failed to delete consultant"}

@app.delete("/api/consultants")
async def delete_consultants_batch(request: DeleteRequest) -> Dict[str, Any]:
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
            logger.warning(f"Batch delete completed with {len(errors)} error(s): {deleted_count} deleted")
            return {
                "success": True,
                "message": f"Deleted {deleted_count} consultant(s), {len(errors)} error(s)",
                "deleted_count": deleted_count,
                "errors": errors
            }
        
        logger.info(f"Successfully deleted {deleted_count} consultant(s)")
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} consultant(s)",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error("Error deleting consultants in batch", exc_info=True, extra={"count": len(request.ids)})
        return {"success": False, "error": "Failed to delete consultants"}

@app.post("/api/resumes/upload")
async def upload_resume(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a PDF resume, parse it, and create a Consultant entry in Weaviate.
    Returns the consultant object with ID.
    """
    if not consultant_service:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    # Generate UUID for consultant
    consultant_id = str(uuid.uuid4())
    
    try:
        # Read PDF bytes
        pdf_bytes = await file.read()
        
        # Check if file is empty
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Validate file type - check filename, content type, and PDF magic bytes
        filename = file.filename or ""
        content_type = file.content_type or ""
        is_pdf_filename = filename.endswith('.pdf')
        is_pdf_content_type = content_type == 'application/pdf' or 'pdf' in content_type.lower()
        is_pdf_magic_bytes = pdf_bytes.startswith(b'%PDF')
        
        # Log for debugging (especially useful in CI)
        logger.debug(f"File upload validation - filename: {filename}, content_type: {content_type}, size: {len(pdf_bytes)}, has_pdf_magic: {is_pdf_magic_bytes}")
        
        # More lenient validation: if filename or content type suggests PDF, check magic bytes
        # Otherwise, require magic bytes to be present
        if is_pdf_filename or is_pdf_content_type:
            # If filename or content type suggests PDF, require magic bytes
            if not is_pdf_magic_bytes:
                raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF (missing PDF magic bytes)")
        elif not is_pdf_magic_bytes:
            # If no PDF indicators, require magic bytes
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        logger.info(f"Uploading resume: {filename} ({len(pdf_bytes)} bytes)")
        
        # Parse resume - returns ConsultantData (pass bytes directly)
        consultant_data = parse_resume_pdf(pdf_bytes)
        
        # Save PDF to storage using consultant_id
        storage.save_pdf(pdf_bytes, consultant_id)
        
        # Insert into Weaviate Consultant collection with consultant_id as UUID
        consultant_service.create_consultant(consultant_data, consultant_id)
        
        logger.info(f"Successfully uploaded and processed resume for {consultant_data.name} (ID: {consultant_id})")
        
        # Return consultant object with ID and resumeId
        consultant_dict = consultant_data.model_dump()
        return {
            "id": consultant_id,
            **consultant_dict,
            "resumeId": consultant_id
        }
    
    except ValueError as e:
        # Clean up PDF if parsing failed (client error - invalid PDF format)
        try:
            pdf_path = storage.get_path(consultant_id)
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except (OSError, ValueError) as cleanup_error:
            logger.warning(f"Failed to cleanup PDF after parse error: {cleanup_error}")
        logger.error(f"Error parsing resume: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error parsing resume: {str(e)}")
    except RuntimeError as e:
        # RuntimeError from OpenAI API failures should return 500
        try:
            pdf_path = storage.get_path(consultant_id)
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except (OSError, ValueError) as cleanup_error:
            logger.warning(f"Failed to cleanup PDF after OpenAI error: {cleanup_error}")
        logger.error(f"OpenAI API error during resume parsing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing resume. Please try again later.")
    except HTTPException:
        # Re-raise HTTPException as-is (e.g., validation errors)
        raise
    except Exception as e:
        # Clean up PDF if Weaviate insertion failed
        try:
            pdf_path = storage.get_path(consultant_id)
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except (OSError, ValueError) as cleanup_error:
            logger.warning(f"Failed to cleanup PDF after upload error: {cleanup_error}")
        
        logger.error("Error uploading resume", exc_info=True, extra={"upload_filename": file.filename})
        raise HTTPException(status_code=500, detail="Error processing resume. Please try again later.")

@app.get("/api/resumes/{resume_id}/pdf")
async def get_resume_pdf(resume_id: str) -> FileResponse:
    """
    Retrieve the original PDF file by consultant/resume ID.
    The ID is the same as the consultant ID for uploaded resumes.
    """
    try:
        file_path = storage.get_path(resume_id)
        if not os.path.exists(file_path):
            logger.warning(f"PDF not found for resume_id: {resume_id}")
            raise HTTPException(status_code=404, detail="PDF not found")
        
        logger.debug(f"Retrieving PDF for resume_id: {resume_id}")
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=f"{resume_id}.pdf"
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        logger.warning(f"PDF file not found for resume_id: {resume_id}")
        raise HTTPException(status_code=404, detail="PDF not found")
    except Exception as e:
        logger.error(f"Error retrieving PDF for resume_id: {resume_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving PDF")
@app.get("/api/overview", response_model=OverviewResponse)
async def get_overview() -> OverviewResponse:
    """
    Get overview statistics: number of CVs (consultants), unique skills, and top 10 most common skills.
    """
    if not overview_service:
        return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])
    
    return overview_service.get_overview()

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint for interactive team assembly conversation.
    Uses OpenAI to ask clarifying questions and generate role queries.
    """
    global chat_service
    
    # Initialize chat service lazily
    if not chat_service:
        try:
            chat_service = ChatService()
            logger.info("Chat service initialized")
        except ValueError as e:
            logger.error("Failed to initialize chat service", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    try:
        logger.debug(f"Processing chat request with {len(request.messages)} messages")
        response = chat_service.process_chat(request.messages)
        if response.isComplete:
            logger.info(f"Chat completed with {len(response.roles or [])} roles generated")
        return response
    except Exception as e:
        logger.error("Error in chat endpoint", exc_info=True, extra={"message_count": len(request.messages)})
        raise HTTPException(status_code=500, detail="Error processing chat. Please try again later.")

@app.post("/api/consultants/match-roles", response_model=RoleMatchResponse)
async def match_consultants_by_roles(request: RoleMatchRequest) -> RoleMatchResponse:
    """
    Match consultants for multiple roles using vector search.
    Performs a separate vector search for each role query.
    """
    if not matching_service:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    try:
        role_results = []
        
        for role_query in request.roles:
            logger.debug(f"Searching for role '{role_query.title}' with query: '{role_query.query}'")
            
            try:
                consultants = matching_service.match_consultants_by_role(role_query.query, limit=3)
            except ValueError as e:
                # If no matches found, return empty list for this role
                logger.warning(f"No matches found for role '{role_query.title}': {e}")
                consultants = []
            
            # Ensure consultants is always a list, never None
            if consultants is None:
                consultants = []
            
            role_result = RoleMatchResult(
                role=role_query,
                consultants=consultants
            )
            logger.info(f"Role '{role_query.title}': Found {len(consultants)} consultants")
            role_results.append(role_result)
        
        response_data = RoleMatchResponse(roles=role_results)
        logger.info(f"Match roles response: {len(response_data.roles)} roles processed")
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Check if it's a schema-related error
        if "no graphql provider" in error_msg.lower() or "no schema" in error_msg.lower():
            logger.warning("Schema not initialized for role matching")
            raise HTTPException(
                status_code=422,
                detail="No consultants found in database. Please upload consultant resumes first."
            )
        logger.error("Error matching consultants by roles", exc_info=True, extra={"role_count": len(request.roles)})
        raise HTTPException(status_code=500, detail="Error matching consultants. Please try again later.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

