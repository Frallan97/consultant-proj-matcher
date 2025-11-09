"""
Service for consultant-related operations with Weaviate.
"""
import asyncio
import weaviate
from typing import List, Dict, Optional
from models import ConsultantData
from logger_config import get_logger

logger = get_logger(__name__)


class ConsultantService:
    """Service for managing consultants in Weaviate."""
    
    def __init__(self, client: weaviate.Client):
        """Initialize with Weaviate client."""
        self.client = client
    
    async def schema_exists(self) -> bool:
        """Check if the Consultant schema exists in Weaviate."""
        if not self.client:
            return False
        try:
            schema = await asyncio.to_thread(self.client.schema.get)
            class_names = [c["class"] for c in schema.get("classes", [])]
            return "Consultant" in class_names
        except (weaviate.exceptions.WeaviateBaseError, Exception) as e:
            logger.error("Error checking schema", exc_info=True)
            return False
    
    async def create_consultant(self, consultant_data: ConsultantData, consultant_id: str) -> None:
        """Create a consultant in Weaviate."""
        consultant_dict = consultant_data.model_dump()
        await asyncio.to_thread(
            self.client.data_object.create,
            data_object=consultant_dict,
            class_name="Consultant",
            uuid=consultant_id
        )
    
    async def get_all_consultants(self, limit: int = 100) -> List[Dict]:
        """Get all consultants from Weaviate."""
        if not self.client or not await self.schema_exists():
            return []
        
        try:
            def _get_consultants():
                return (
                    self.client.query
                    .get("Consultant", ["name", "email", "phone", "skills", "availability", "experience", "education"])
                    .with_additional(["id"])
                    .with_limit(limit)
                    .do()
                )
            
            response = await asyncio.to_thread(_get_consultants)
            
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
        except (weaviate.exceptions.WeaviateBaseError, Exception) as e:
            logger.error("Error fetching consultants", exc_info=True)
            return []
    
    async def delete_consultant(self, consultant_id: str) -> bool:
        """Delete a consultant by ID."""
        if not self.client:
            return False
        
        try:
            await asyncio.to_thread(
                self.client.data_object.delete,
                uuid=consultant_id,
                class_name="Consultant"
            )
            return True
        except (weaviate.exceptions.WeaviateBaseError, Exception) as e:
            logger.error(f"Error deleting consultant {consultant_id}", exc_info=True, extra={"consultant_id": consultant_id})
            return False
    
    async def delete_consultants_batch(self, consultant_ids: List[str]) -> tuple[int, List[Dict]]:
        """Delete multiple consultants by IDs. Returns (deleted_count, errors)."""
        if not self.client:
            return (0, [{"error": "Weaviate client not available"}])
        
        deleted_count = 0
        errors = []
        
        for consultant_id in consultant_ids:
            try:
                await asyncio.to_thread(
                    self.client.data_object.delete,
                    uuid=consultant_id,
                    class_name="Consultant"
                )
                deleted_count += 1
            except Exception as e:
                errors.append({"id": consultant_id, "error": str(e)})
        
        return (deleted_count, errors)
    
    async def get_consultants_for_overview(self, limit: int = 500) -> List[Dict]:
        """Get consultants for overview statistics (only skills needed)."""
        if not self.client or not await self.schema_exists():
            return []
        
        try:
            def _get_consultants():
                return (
                    self.client.query
                    .get("Consultant", ["skills"])
                    .with_limit(limit)
                    .do()
                )
            
            response = await asyncio.to_thread(_get_consultants)
            
            consultants = []
            if "data" in response and "Get" in response["data"] and "Consultant" in response["data"]["Get"]:
                results = response["data"]["Get"]["Consultant"]
                for consultant in results:
                    consultants.append({
                        "skills": consultant.get("skills", [])
                    })
            
            return consultants
        except (weaviate.exceptions.WeaviateBaseError, Exception) as e:
            logger.error("Error fetching consultants for overview", exc_info=True)
            return []

