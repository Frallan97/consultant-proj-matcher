"""
Shared data models for consultant data.
"""
from pydantic import BaseModel
from typing import List, Optional


class ConsultantData(BaseModel):
    """Shared consultant data structure used by parser and API."""
    name: str
    email: str
    phone: str
    skills: List[str]
    experience: str
    education: str
    availability: str = "available"


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request for chat endpoint."""
    messages: List[ChatMessage]


class RoleQuery(BaseModel):
    """Role query for vector search."""
    title: str
    description: str
    query: str  # Vector search query
    requiredSkills: List[str]


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    role: str
    content: str
    isComplete: bool
    roles: Optional[List[RoleQuery]] = None


class RoleMatchRequest(BaseModel):
    """Request for role-based matching."""
    roles: List[RoleQuery]


class RoleMatchResult(BaseModel):
    """Result for a single role match."""
    role: RoleQuery
    consultants: List[dict] = []  # List of Consultant dictionaries, default to empty list


class RoleMatchResponse(BaseModel):
    """Response from role-based matching."""
    roles: List[RoleMatchResult]


class SkillCount(BaseModel):
    """Skill count for overview statistics."""
    skill: str
    count: int


class OverviewResponse(BaseModel):
    """Response for overview statistics."""
    cvCount: int
    uniqueSkillsCount: int
    topSkills: List[SkillCount]

