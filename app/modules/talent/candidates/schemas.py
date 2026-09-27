from enum import Enum
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict, Field

class ResumeExtractionSchema(BaseModel):
    """The strict data template forced onto the LLM completion loop."""
    name: Optional[str] = None
    email: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[str] = []
    education: List[str] = []
    languages: List[str] = []

class CandidateResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: Optional[str]
    email: Optional[str]
    summary: Optional[str]
    skills: List[str]
    experience: List[str]
    education: List[str]
    languages: List[str]
    
    model_config = ConfigDict(from_attributes=True)


class RequirementMatchStatus(str, Enum):
    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    NOT_SATISFIED = "not_satisfied"
    NOT_EVIDENCE_FOUND = "not_evidenced"

class EvidentiaryRequirementElement(BaseModel):
    requirement_name: str = Field(..., description="The specific core technical or experiential condition checked.")
    status: RequirementMatchStatus = Field(..., description="The literal level of compliance found inside text.")
    extracted_text_evidence: Optional[str] = Field(None, description="Exact word-for-word textual quote from the candidate profile.")

class CandidateEvaluationSchema(BaseModel):
    """The strict structural template forced onto the downstream LLM processing engine."""
    matched_required_skills: List[str] = []
    missing_required_skills: List[str] = []
    matched_preferred_skills: List[str] = []
    relevant_experience_highlights: List[str] = []
    education_match_explanation: str
    experience_match_rating: str = Field(..., description="Must resolve to: meets_requirement, partially_meets, or does_not_meet")
    evidentiary_checks: List[EvidentiaryRequirementElement] = Field(..., description="Granular checklist mapping requirements to explicit text evidence.")
    explanation: str = Field(..., description="Objective, non-prose professional synthesis detailing the fit.")
    confidence: float = Field(..., description="Mathematical accuracy metric from 0.0 to 1.0 based on structural evidence availability.")

class CandidateEvaluationResponse(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    evaluation: CandidateEvaluationSchema
    
class MatchSummaryResponse(BaseModel):
    """The formatted scannable presentation layer returned to the UI dashboard."""
    candidate_id: uuid.UUID
    candidate_name: str
    job_title: str
    required_skills_check: Dict[str, str] = Field(..., description="Maps skill to indicator glyph: ✓ or ✗")
    preferred_skills_check: Dict[str, str] = Field(..., description="Maps skill to indicator glyph: ✓, ✗, or ?")
    experience_status: str
    executive_summary: str
    
class BlindEvaluationResultSchema(BaseModel):
    """The clean structural data forced onto the LLM output buffer."""
    anonymized_id: str = Field(..., description="Anonymized ID format e.g., C-1042")
    required_skills_check: Dict[str, str] = Field(..., description="Maps requirements directly to symbols: ✓ or ✗")
    missing_requirements: List[str] = []
    relevant_experience_highlights: List[str] = []
    experience_requirement_rating: str = Field(..., description="Must be: Meets, Partially Meets, or Does Not Meet")
    ai_evaluation_summary: str = Field(..., description="Objective structural analysis of the candidate's alignment.")
    adversarial_attack_detected: bool = Field(..., description="Flags if untrusted content attempted a prompt injection.")

class BlindEvaluationResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    organization_id: uuid.UUID
    model_provider: str
    estimated_cost: float
    evaluation: BlindEvaluationResultSchema
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)