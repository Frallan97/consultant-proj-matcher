"""
Service for consultant-related operations with Weaviate.
"""
import weaviate
from typing import List, Dict, Optional
from models import ConsultantData


class ConsultantService:
    """Service for managing consultants in Weaviate."""
    
    def __init__(self, client: weaviate.Client):
        """Initialize with Weaviate client."""
        self.client = client
    
    def schema_exists(self) -> bool:
        """Check if the Consultant schema exists in Weaviate."""
        if not self.client:
            return False
        try:
            schema = self.client.schema.get()
            class_names = [c["class"] for c in schema.get("classes", [])]
            return "Consultant" in class_names
        except Exception as e:
            print(f"Error checking schema: {e}")
            return False
    
    def create_consultant(self, consultant_data: ConsultantData, consultant_id: str) -> None:
        """Create a consultant in Weaviate."""
        consultant_dict = consultant_data.model_dump()
        self.client.data_object.create(
            data_object=consultant_dict,
            class_name="Consultant",
            uuid=consultant_id
        )
    
    def get_all_consultants(self, limit: int = 100) -> List[Dict]:
        """Get all consultants from Weaviate."""
        if not self.client or not self.schema_exists():
            return []
        
        try:
            response = (
                self.client.query
                .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
                .with_additional(["id"])
                .with_limit(limit)
                .do()
            )
            
            consultants = []
            if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
                results = response["data"]["Get"]["Consultant"]
                for consultant in results:
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
                    consultants.append(consultant_data)
            
            return consultants
        except Exception as e:
            print(f"Error fetching consultants: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def delete_consultant(self, consultant_id: str) -> bool:
        """Delete a consultant by ID."""
        if not self.client:
            return False
        
        try:
            self.client.data_object.delete(
                uuid=consultant_id,
                class_name="Consultant"
            )
            return True
        except Exception as e:
            print(f"Error deleting consultant {consultant_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_consultants_batch(self, consultant_ids: List[str]) -> tuple[int, List[Dict]]:
        """Delete multiple consultants by IDs. Returns (deleted_count, errors)."""
        if not self.client:
            return (0, [{"error": "Weaviate client not available"}])
        
        deleted_count = 0
        errors = []
        
        for consultant_id in consultant_ids:
            try:
                self.client.data_object.delete(
                    uuid=consultant_id,
                    class_name="Consultant"
                )
                deleted_count += 1
            except Exception as e:
                errors.append({"id": consultant_id, "error": str(e)})
        
        return (deleted_count, errors)
    
    def get_consultants_for_overview(self, limit: int = 500) -> List[Dict]:
        """Get consultants for overview statistics (only skills needed)."""
        if not self.client or not self.schema_exists():
            return []
        
        try:
            response = (
                self.client.query
                .get("Consultant", ["skills"])
                .with_limit(limit)
                .do()
            )
            
            consultants = []
            if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
                results = response["data"]["Get"]["Consultant"]
                for consultant in results:
                    consultants.append({
                        "skills": consultant.get("skills", [])
                    })
            
            return consultants
        except Exception as e:
            print(f"Error fetching consultants for overview: {e}")
            return []

