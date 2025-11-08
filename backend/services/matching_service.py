"""
Service for matching consultants using vector search.
"""
import weaviate
from typing import List, Dict, Optional
from services.consultant_service import ConsultantService


class MatchingService:
    """Service for matching consultants using Weaviate vector search."""
    
    def __init__(self, client: weaviate.Client, consultant_service: ConsultantService, storage):
        """Initialize with Weaviate client, consultant service, and storage."""
        self.client = client
        self.consultant_service = consultant_service
        self.storage = storage
        self.MIN_CERTAINTY = 0.2  # Lower threshold to get more diverse results
    
    def _calculate_match_score(self, certainty: Optional[float]) -> float:
        """Calculate match score from Weaviate certainty (0-1) to percentage (0-90)."""
        try:
            certainty_value = float(certainty) if certainty is not None else self.MIN_CERTAINTY
        except (ValueError, TypeError):
            certainty_value = self.MIN_CERTAINTY
        
        # Map certainty 0.0-0.9 to 0-90% (cap at 90%)
        # This provides more realistic match scores - even the best matches rarely exceed 90%
        match_score = min(round(certainty_value * 100, 1), 90.0)
        return match_score
    
    def _enrich_consultant_data(self, consultant: Dict, consultant_id: str, match_score: Optional[float] = None) -> Dict:
        """Enrich consultant data with ID, match score, and resume ID."""
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
        
        if match_score is not None:
            consultant_data["matchScore"] = match_score
        
        # Check if PDF exists for this consultant
        try:
            import os
            pdf_path = self.storage.get_path(consultant_id)
            if os.path.exists(pdf_path):
                consultant_data["resumeId"] = consultant_id
        except:
            pass
        
        return consultant_data
    
    def match_consultants(self, project_description: str, limit: int = 3) -> List[Dict]:
        """Match consultants based on project description using vector search."""
        if not self.client:
            raise ValueError("Weaviate client not available")
        
        if not self.consultant_service.schema_exists():
            raise ValueError("No consultants found in database. Please upload consultant resumes first.")
        
        try:
            # Fetch a large pool of candidates to score them all, then limit to top N
            response = (
                self.client.query
                .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
                .with_near_text({
                    "concepts": [project_description],
                    "certainty": self.MIN_CERTAINTY
                })
                .with_additional(["id", "certainty"])
                .with_limit(100)  # Get large pool to score all candidates
                .do()
            )
            
            consultants = []
            if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
                results = response["data"]["Get"]["Consultant"]
                
                # Calculate scores for ALL candidates first
                for consultant in results:
                    consultant_id = consultant.get("_additional", {}).get("id")
                    additional = consultant.get("_additional", {})
                    
                    # Get certainty from Weaviate vector search
                    certainty_raw = additional.get("certainty", None)
                    match_score = self._calculate_match_score(certainty_raw)
                    
                    consultant_data = self._enrich_consultant_data(consultant, consultant_id, match_score)
                    consultants.append(consultant_data)
                
                # Now limit to top N AFTER calculating scores for all candidates
                consultants = sorted(consultants, key=lambda x: x["matchScore"], reverse=True)[:limit]
            
            return consultants
        
        except ValueError:
            raise
        except Exception as e:
            error_msg = str(e)
            # Check if it's a schema-related error
            if "no graphql provider" in error_msg.lower() or "no schema" in error_msg.lower():
                raise ValueError("No consultants found in database. Please upload consultant resumes first.")
            print(f"Error matching consultants: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error matching consultants: {error_msg}")
    
    def match_consultants_by_role(self, role_query: str, limit: int = 3) -> List[Dict]:
        """Match consultants for a single role query using vector search."""
        if not self.client:
            raise ValueError("Weaviate client not available")
        
        if not self.consultant_service.schema_exists():
            raise ValueError("No consultants found in database. Please upload consultant resumes first.")
        
        try:
            # Perform vector search for this role
            # No certainty threshold - get all matches, we'll sort by score
            response = (
                self.client.query
                .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
                .with_near_text({
                    "concepts": [role_query]
                    # No certainty threshold - get all matches
                })
                .with_additional(["id", "certainty"])
                .with_limit(100)  # Get large pool to score all candidates
                .do()
            )
            
            consultants = []
            if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
                results = response["data"]["Get"]["Consultant"]
                
                # Calculate scores for ALL candidates first
                for consultant in results:
                    consultant_id = consultant.get("_additional", {}).get("id")
                    additional = consultant.get("_additional", {})
                    
                    # Get certainty from Weaviate vector search
                    certainty_raw = additional.get("certainty", None)
                    match_score = self._calculate_match_score(certainty_raw)
                    
                    consultant_data = self._enrich_consultant_data(consultant, consultant_id, match_score)
                    consultants.append(consultant_data)
            
            # If no matches found, try fallback query
            if len(consultants) == 0:
                try:
                    # Fallback: get all consultants without vector search
                    fallback_response = (
                        self.client.query
                        .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
                        .with_additional(["id"])
                        .with_limit(10)  # Get top 10 consultants as fallback
                        .do()
                    )
                    
                    if "data" in fallback_response and "Get" in fallback_response["data"] and "Consultant" in fallback_response["data"]["Get"]:
                        fallback_results = fallback_response["data"]["Get"]["Consultant"]
                        
                        for consultant in fallback_results:
                            consultant_id = consultant.get("_additional", {}).get("id")
                            
                            consultant_data = self._enrich_consultant_data(consultant, consultant_id, 10.0)  # Low score for fallback matches
                            consultants.append(consultant_data)
                except Exception as e:
                    print(f"Error in fallback query: {e}")
            
            # Now limit to top N AFTER calculating scores for all candidates
            consultants = sorted(consultants, key=lambda x: x["matchScore"], reverse=True)[:limit]
            
            # Ensure consultants is always a list, never None
            if consultants is None:
                consultants = []
            
            return consultants
        
        except ValueError:
            raise
        except Exception as e:
            error_msg = str(e)
            # Check if it's a schema-related error
            if "no graphql provider" in error_msg.lower() or "no schema" in error_msg.lower():
                raise ValueError("No consultants found in database. Please upload consultant resumes first.")
            print(f"Error matching consultants by role: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error matching consultants: {error_msg}")

