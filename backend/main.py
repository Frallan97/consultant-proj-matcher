from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import weaviate
import os
import uuid
import json
from dotenv import load_dotenv
from openai import OpenAI
from storage import LocalFileStorage
from services.resume_parser import parse_resume_pdf
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

# Helper function to check if Consultant schema exists
def schema_exists():
    """Check if the Consultant schema exists in Weaviate."""
    if not client:
        return False
    try:
        schema = client.schema.get()
        class_names = [c["class"] for c in schema.get("classes", [])]
        return "Consultant" in class_names
    except Exception as e:
        print(f"Error checking schema: {e}")
        return False

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
    if not client:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "reason": "Weaviate client not available"}
        )
    
    if not schema_exists():
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
    if not client:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    if not schema_exists():
        raise HTTPException(
            status_code=422,
            detail="No consultants found in database. Please upload consultant resumes first."
        )
    
    try:
        # Use Weaviate's pure vector search (semantic similarity)
        # .with_near_text() generates a vector from the query text and compares it to stored object vectors
        # Use certainty (0-1) instead of distance for better score differentiation
        # Certainty represents similarity: 1.0 = identical, 0.0 = completely different
        MIN_CERTAINTY = 0.2  # Lower threshold to get more diverse results
        
        # Fetch a large pool of candidates to score them all, then limit to top 3
        response = (
            client.query
            .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
            .with_near_text({
                "concepts": [project.projectDescription],
                "certainty": MIN_CERTAINTY
            })
            .with_additional(["id", "certainty"])
            .with_limit(100)  # Get large pool to score all candidates
            .do()
        )
        
        consultants = []
        if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
            results = response["data"]["Get"]["Consultant"]
            
            # Collect all certainties for normalization across all candidates
            certainties = []
            for consultant in results:
                additional = consultant.get("_additional", {})
                certainty_raw = additional.get("certainty", None)
                if certainty_raw is not None:
                    try:
                        certainties.append(float(certainty_raw))
                    except (ValueError, TypeError):
                        pass
            
            # Normalize scores to use full 0-100% range based on all candidates
            min_certainty = min(certainties) if certainties else 0.0
            max_certainty = max(certainties) if certainties else 1.0
            certainty_range = max_certainty - min_certainty if max_certainty > min_certainty else 1.0
            
            # Calculate scores for ALL candidates first
            for consultant in results:
                consultant_id = consultant.get("_additional", {}).get("id")
                additional = consultant.get("_additional", {})
                
                # Get certainty from Weaviate vector search
                # Certainty ranges from 0.0 (completely different) to 1.0 (identical)
                certainty_raw = additional.get("certainty", None)
                try:
                    certainty = float(certainty_raw) if certainty_raw is not None else MIN_CERTAINTY
                except (ValueError, TypeError):
                    certainty = MIN_CERTAINTY
                
                # Normalize certainty to 0-100% scale using the full range of results
                # This ensures better differentiation between candidates
                if certainty_range > 0:
                    normalized_certainty = (certainty - min_certainty) / certainty_range
                    match_score = round(normalized_certainty * 100, 1)
                else:
                    # Fallback: use certainty directly if all values are the same
                    match_score = round(certainty * 100, 1)
                
                consultant_data = {
                    "id": consultant_id,
                    "name": consultant.get("name", ""),
                    "email": consultant.get("email", ""),
                    "phone": consultant.get("phone", ""),
                    "skills": consultant.get("skills", []),
                    "availability": consultant.get("availability", "available"),
                    "experience": consultant.get("experience", ""),
                    "education": consultant.get("education", ""),
                    "matchScore": match_score,
                    "resumeId": None
                }
                
                # Check if PDF exists for this consultant
                try:
                    pdf_path = storage.get_path(consultant_id)
                    if os.path.exists(pdf_path):
                        consultant_data["resumeId"] = consultant_id
                except:
                    pass
                
                consultants.append(consultant_data)
            
            # Now limit to top 3 AFTER calculating scores for all candidates
            consultants = sorted(consultants, key=lambda x: x["matchScore"], reverse=True)[:3]
        
        return ConsultantResponse(consultants=consultants)
    
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
        print(f"Error matching consultants: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error matching consultants: {error_msg}")

@app.get("/api/consultants", response_model=ConsultantResponse)
async def get_all_consultants():
    """
    Get all consultants.
    """
    if not client:
        return ConsultantResponse(consultants=[])
    
    if not schema_exists():
        return ConsultantResponse(consultants=[])
    
    try:
        response = (
            client.query
            .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
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
                
                consultant_data = {
                    "id": consultant_id,
                    "name": consultant.get("name", ""),
                    "email": consultant.get("email", ""),
                    "phone": consultant.get("phone", ""),
                    "skills": consultant.get("skills", []),
                    "availability": consultant.get("availability", "available"),
                    "experience": consultant.get("experience", ""),
                    "education": consultant.get("education", ""),
                    "resumeId": None
                }
                
                # Check if PDF exists for this consultant
                try:
                    pdf_path = storage.get_path(consultant_id)
                    if os.path.exists(pdf_path):
                        consultant_data["resumeId"] = consultant_id
                except:
                    pass
                
                consultants.append(consultant_data)
        
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
        
        # Parse resume - returns ConsultantData (pass bytes directly)
        consultant_data = parse_resume_pdf(pdf_bytes)
        
        # Save PDF to storage using consultant_id
        storage.save_pdf(pdf_bytes, consultant_id)
        
        # Insert into Weaviate Consultant collection with consultant_id as UUID
        # Convert ConsultantData to dict for Weaviate
        consultant_dict = consultant_data.model_dump()
        client.data_object.create(
            data_object=consultant_dict,
            class_name="Consultant",
            uuid=consultant_id
        )
        
        # Return consultant object with ID and resumeId
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
    try:
        if not client:
            print("Warning: Weaviate client not available for overview")
            return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])
        
        if not schema_exists():
            print("Warning: Consultant schema does not exist for overview")
            return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])
        
        # Fetch all consultants to count and collect skills
        # Use a reasonable limit to avoid timeouts
        print("Fetching consultants for overview...")
        response = (
            client.query
            .get("Consultant", ["skills"])
            .with_limit(500)  # Reduced limit to avoid timeouts
            .do()
        )
        print(f"Overview query completed, processing results...")
        
        cv_count = 0
        all_skills = set()
        skill_counts = {}  # Dictionary to count occurrences of each skill
        
        if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
            results = response["data"]["Get"]["Consultant"]
            cv_count = len(results)
            print(f"Found {cv_count} consultants for overview")
            
            # Collect all unique skills and count occurrences
            for consultant in results:
                skills = consultant.get("skills", [])
                if skills:
                    all_skills.update(skills)
                    for skill in skills:
                        skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        # Get top 10 most common skills
        sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        top_skills = [SkillCount(skill=skill, count=count) for skill, count in sorted_skills[:10]]
        
        print(f"Overview complete: {cv_count} CVs, {len(all_skills)} unique skills")
        return OverviewResponse(
            cvCount=cv_count,
            uniqueSkillsCount=len(all_skills),
            topSkills=top_skills
        )
    
    except Exception as e:
        print(f"Error fetching overview: {e}")
        import traceback
        traceback.print_exc()
        # Return empty response instead of raising exception to avoid breaking the UI
        return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for interactive team assembly conversation.
    Uses OpenAI to ask clarifying questions and generate role queries.
    """
    api_key = os.getenv("OPENAI_APIKEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_APIKEY not found in environment variables")
    
    client_openai = OpenAI(api_key=api_key)
    
    # System prompt for team assembly
    system_prompt = """You are a helpful assistant helping assemble a development team. 
Your goal is to quickly understand project requirements and generate a team FAST.

URGENCY DETECTION:
- If the user mentions being in a hurry, urgent, ASAP, quickly, fast, or any time pressure - generate roles IMMEDIATELY with zero questions
- If the user provides ANY project description, generate roles immediately - don't ask questions
- Only ask questions if the message is completely empty or just "hello" with no context

Be extremely proactive and make reasonable assumptions. Generate roles on the FIRST message if possible.

Guidelines:
- If the user mentions a project type (web app, mobile app, game, API, etc.), generate appropriate roles IMMEDIATELY
- Make reasonable assumptions about tech stack based on project type if not specified
- For web apps, typically include: Frontend Engineer, Backend Engineer (and optionally Full-stack, DevOps, Designer)
- For mobile apps, typically include: Mobile Developer (iOS/Android), Backend Engineer
- For games, typically include: Game Developer, Backend Engineer, Designer
- For APIs/backend services: Backend Engineer, DevOps Engineer
- For data/ML projects: Data Engineer, ML Engineer, Backend Engineer
- Default to common modern stacks (React, Node.js, Python, etc.) if not specified

Generate structured role queries in JSON format. The JSON should be embedded in your response like this:

<roles>
{
  "roles": [
    {
      "title": "Frontend Engineer",
      "description": "Description of what this role needs",
      "query": "Vector search query for matching candidates (e.g., 'Frontend developer with React and TypeScript experience')",
      "requiredSkills": ["React", "TypeScript"]
    }
  ]
}
</roles>

CRITICAL: Generate roles IMMEDIATELY when you detect urgency or when the user provides any project information. 
Don't ask questions - be decisive and helpful. Speed is more important than perfect information."""
    
    try:
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Call OpenAI
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7
        )
        
        if not response.choices or len(response.choices) == 0:
            raise HTTPException(status_code=500, detail="OpenAI API returned no choices")
        
        content = response.choices[0].message.content
        
        # Check if response contains role queries
        is_complete = False
        roles = None
        
        if "<roles>" in content and "</roles>" in content:
            try:
                roles_start = content.find("<roles>") + len("<roles>")
                roles_end = content.find("</roles>")
                roles_json = content[roles_start:roles_end].strip()
                roles_data = json.loads(roles_json)
                roles = [RoleQuery(**role) for role in roles_data.get("roles", [])]
                is_complete = True
                # Remove the roles tag from the content
                content = content[:content.find("<roles>")].strip() + content[content.find("</roles>") + len("</roles>"):].strip()
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error parsing roles from OpenAI response: {e}")
                # Continue without roles
        
        return ChatResponse(
            role="assistant",
            content=content,
            isComplete=is_complete,
            roles=roles
        )
    
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
    if not client:
        raise HTTPException(status_code=503, detail="Weaviate client not available")
    
    if not schema_exists():
        raise HTTPException(
            status_code=422,
            detail="No consultants found in database. Please upload consultant resumes first."
        )
    
    try:
        role_results = []
        
        for role_query in request.roles:
            # Perform vector search for this role
            # Remove certainty threshold to get ALL matches, even if they're bad
            # We'll sort by score and take the top matches
            print(f"Searching for role '{role_query.title}' with query: '{role_query.query}'")
            
            # First try vector search without certainty threshold to get all matches
            response = (
                client.query
                .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
                .with_near_text({
                    "concepts": [role_query.query]
                    # No certainty threshold - get all matches
                })
                .with_additional(["id", "certainty"])
                .with_limit(100)  # Get large pool to score all candidates
                .do()
            )
            
            consultants = []
            if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
                results = response["data"]["Get"]["Consultant"]
                print(f"Found {len(results)} raw results for role '{role_query.title}'")
                
                # Collect all certainties for normalization across all candidates
                certainties = []
                for consultant in results:
                    additional = consultant.get("_additional", {})
                    certainty_raw = additional.get("certainty", None)
                    if certainty_raw is not None:
                        try:
                            certainties.append(float(certainty_raw))
                        except (ValueError, TypeError):
                            pass
                
                # Normalize scores to use full 0-100% range based on all candidates
                min_certainty = min(certainties) if certainties else 0.0
                max_certainty = max(certainties) if certainties else 1.0
                certainty_range = max_certainty - min_certainty if max_certainty > min_certainty else 1.0
                
                # Calculate scores for ALL candidates first
                for consultant in results:
                    consultant_id = consultant.get("_additional", {}).get("id")
                    additional = consultant.get("_additional", {})
                    
                    # Get certainty from Weaviate vector search
                    # Certainty ranges from 0.0 (completely different) to 1.0 (identical)
                    certainty_raw = additional.get("certainty", None)
                    try:
                        certainty = float(certainty_raw) if certainty_raw is not None else 0.0
                    except (ValueError, TypeError):
                        certainty = 0.0
                    
                    # Normalize certainty to 0-100% scale using the full range of results
                    # This ensures better differentiation between candidates
                    if certainty_range > 0:
                        normalized_certainty = (certainty - min_certainty) / certainty_range
                        match_score = round(normalized_certainty * 100, 1)
                    else:
                        # Fallback: use certainty directly if all values are the same
                        match_score = round(certainty * 100, 1)
                    
                    consultant_data = {
                        "id": consultant_id,
                        "name": consultant.get("name", ""),
                        "email": consultant.get("email", ""),
                        "phone": consultant.get("phone", ""),
                        "skills": consultant.get("skills", []),
                        "availability": consultant.get("availability", "available"),
                        "experience": consultant.get("experience", ""),
                        "education": consultant.get("education", ""),
                        "matchScore": match_score,
                        "resumeId": None
                    }
                    
                    # Check if PDF exists
                    try:
                        pdf_path = storage.get_path(consultant_id)
                        if os.path.exists(pdf_path):
                            consultant_data["resumeId"] = consultant_id
                    except:
                        pass
                    
                    consultants.append(consultant_data)
            
            # If no matches found, try to get any consultants as fallback
            if len(consultants) == 0:
                print(f"No vector matches found for '{role_query.title}', trying fallback query...")
                try:
                    # Fallback: get all consultants without vector search
                    fallback_response = (
                        client.query
                        .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
                        .with_additional(["id"])
                        .with_limit(10)  # Get top 10 consultants as fallback
                        .do()
                    )
                    
                    if "data" in fallback_response and "Get" in fallback_response["data"] and "Consultant" in fallback_response["data"]["Get"]:
                        fallback_results = fallback_response["data"]["Get"]["Consultant"]
                        print(f"Found {len(fallback_results)} fallback consultants for role '{role_query.title}'")
                        
                        for consultant in fallback_results:
                            consultant_id = consultant.get("_additional", {}).get("id")
                            
                            consultant_data = {
                                "id": consultant_id,
                                "name": consultant.get("name", ""),
                                "email": consultant.get("email", ""),
                                "phone": consultant.get("phone", ""),
                                "skills": consultant.get("skills", []),
                                "availability": consultant.get("availability", "available"),
                                "experience": consultant.get("experience", ""),
                                "education": consultant.get("education", ""),
                                "matchScore": 10.0,  # Low score for fallback matches
                                "resumeId": None
                            }
                            
                            # Check if PDF exists
                            try:
                                pdf_path = storage.get_path(consultant_id)
                                if os.path.exists(pdf_path):
                                    consultant_data["resumeId"] = consultant_id
                            except:
                                pass
                            
                            consultants.append(consultant_data)
                except Exception as e:
                    print(f"Error in fallback query for '{role_query.title}': {e}")
            
            # Now limit to top 3 AFTER calculating scores for all candidates
            consultants = sorted(consultants, key=lambda x: x["matchScore"], reverse=True)[:3]
            
            # Ensure consultants is always a list, never None
            if consultants is None:
                consultants = []
            
            role_result = RoleMatchResult(
                role=role_query,
                consultants=consultants
            )
            print(f"Role '{role_query.title}': Found {len(consultants)} consultants")
            print(f"Role result consultants type: {type(role_result.consultants)}, length: {len(role_result.consultants) if role_result.consultants else 'None'}")
            print(f"Role result consultants value: {role_result.consultants}")
            role_results.append(role_result)
        
        response_data = RoleMatchResponse(roles=role_results)
        print(f"Response has {len(response_data.roles)} roles")
        for idx, role_result in enumerate(response_data.roles):
            print(f"Response role {idx} '{role_result.role.title}': consultants type={type(role_result.consultants)}, length={len(role_result.consultants) if role_result.consultants else 'None'}")
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

