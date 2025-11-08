"""
Service for overview statistics.
"""
from typing import List, Dict
from services.consultant_service import ConsultantService
from models import SkillCount, OverviewResponse


class OverviewService:
    """Service for generating overview statistics."""
    
    def __init__(self, consultant_service: ConsultantService):
        """Initialize with consultant service."""
        self.consultant_service = consultant_service
    
    def get_overview(self) -> OverviewResponse:
        """Get overview statistics: number of CVs, unique skills, and top 10 most common skills."""
        try:
            if not self.consultant_service.client:
                print("Warning: Weaviate client not available for overview")
                return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])
            
            if not self.consultant_service.schema_exists():
                print("Warning: Consultant schema does not exist for overview")
                return OverviewResponse(cvCount=0, uniqueSkillsCount=0, topSkills=[])
            
            # Fetch all consultants to count and collect skills
            print("Fetching consultants for overview...")
            consultants = self.consultant_service.get_consultants_for_overview(limit=500)
            print(f"Overview query completed, processing results...")
            
            cv_count = len(consultants)
            all_skills = set()
            skill_counts = {}  # Dictionary to count occurrences of each skill
            
            print(f"Found {cv_count} consultants for overview")
            
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

