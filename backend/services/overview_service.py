"""
Service for overview statistics.
"""
from typing import List, Dict
from services.consultant_service import ConsultantService
from models import SkillCount, OverviewResponse
from logger_config import get_logger

logger = get_logger(__name__)


class OverviewService:
    """Service for generating overview statistics."""
    
    def __init__(self, consultant_service: ConsultantService):
        """Initialize with consultant service."""
        self.consultant_service = consultant_service
    
    async def get_overview(self) -> OverviewResponse:
        """Get overview statistics: number of CVs, unique skills, and top 10 most common skills."""
        try:
            if not self.consultant_service.client:
                logger.warning("Weaviate client not available for overview")
                return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])
            
            if not await self.consultant_service.schema_exists():
                logger.warning("Consultant schema does not exist for overview")
                return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])
            
            # Fetch all consultants to count and collect skills
            logger.debug("Fetching consultants for overview...")
            consultants = await self.consultant_service.get_consultants_for_overview(limit=500)
            logger.debug("Overview query completed, processing results...")
            
            cv_count = len(consultants)
            all_skills = set()
            skill_counts: Dict[str, int] = {}  # Dictionary to count occurrences of each skill
            
            logger.debug(f"Found {cv_count} consultants for overview")
            
            # Collect all unique skills and count occurrences
            for consultant in consultants:
                skills = consultant.get("skills", [])
                if skills:
                    all_skills.update(skills)
                    for skill in skills:
                        skill_counts[skill] = skill_counts.get(skill, 0) + 1
            
            # Get top 10 most common skills
            sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
            top_skills = [SkillCount(skill=skill, count=count) for skill, count in sorted_skills[:10]]
            
            logger.info(f"Overview complete: {cv_count} CVs, {len(all_skills)} unique skills")
            return OverviewResponse(
                cvCount=cv_count,
                uniqueSkillsCount=len(all_skills),
                topSkills=top_skills
            )
        
        except Exception as e:
            logger.error("Error fetching overview", exc_info=True)
            # Return empty response instead of raising exception to avoid breaking the UI
            return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])

