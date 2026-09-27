import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class JobProfileExtractionSchema(BaseModel):
    """The strict data structure template forced onto the LLM completion loop."""
    title: str
    seniority: Optional[str] = None
    responsibilities: List[str] = []
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    required_experience: Optional[str] = None
    education: Optional[str] = None
    technologies: List[str] = []

class JobProfileResponse(BaseModel):
    """The data model returned to the frontend client."""
    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    seniority: Optional[str]
    responsibilities: List[str]
    required_skills: List[str]
    preferred_skills: List[str]
    required_experience: Optional[str]
    education: Optional[str]
    technologies: List[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SemanticMatchScoreResponse(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    semantic_match_score: float = Field(..., description="Cosine similarity coordinate distance calculation.")

class RankedMatchElement(BaseModel):
    candidate_id: uuid.UUID
    username: str
    semantic_match_score: float

class RankedMatchesResponse(BaseModel):
    job_id: uuid.UUID
    job_title: str
    ranked_matches: List[RankedMatchElement]
    
class HybridSearchCandidateElement(BaseModel):
    candidate_id: uuid.UUID
    name: str
    semantic_score: float
    skills_score: float
    final_score: float
    seniority: Optional[str]
    years_experience: int
    matched_skills: List[str]

class HybridSearchResponse(BaseModel):
    job_id: uuid.UUID
    query: str
    results: List[HybridSearchCandidateElement]