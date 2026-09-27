import io
import re
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from pypdf import PdfReader

from app.core.database.connection import get_db
from app.core.dependencies import auth_deps
from app.core.database import models as core_models
from app.core.ai_factory.llm import AIFactory
from app.modules.talent.candidates.models import Candidate
from app.modules.talent.candidates.schemas import ResumeExtractionSchema, CandidateResponse, CandidateEvaluationResponse, MatchSummaryResponse, BlindEvaluationResponse, BlindEvaluationResultSchema
from app.modules.talent.candidates.services import CandidateEvaluationWorkflowService, BlindEvaluationResponse, BlindEvaluationWorkflowService
from app.modules.talent.jobs.schemas import SemanticMatchScoreResponse, RankedMatchesResponse
from app.modules.talent.jobs.services import OptimizationMatcherService

router = APIRouter(prefix="/talent", tags=["Talent Ingestion Module"])

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # Strict 5MB limit protecting disk constraints

def sanitize_and_check_injection(text: str) -> str:
    """Heuristically strips malicious HTML script tags and tracks adversarial strings."""
    clean_text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.IGNORECASE)
    
    # Catch adversarial prompt injection overrides hidden in text blocks
    injection_patterns = ["ignore previous instructions", "system override", "you must output"]
    for pattern in injection_patterns:
        if pattern in clean_text.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Guard Triggered: Malicious prompt injection pattern detected inside source document."
            )
    return clean_text

@router.post("/upload-resume", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_process_resume(
    file: UploadFile = File(...),
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Enforce physical validation criteria
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Unsupported media format. Only standard PDF documents are allowed.")
        
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Document payload size limit exceeded (5MB maximum).")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Cannot process blank or empty document binary payloads.")

    # 2. Native document parsing extraction loop
    try:
        pdf_stream = io.BytesIO(contents)
        reader = PdfReader(pdf_stream)
        extracted_raw_text = ""
        for page in reader.pages:
            text_block = page.extract_text()
            if text_block:
                extracted_raw_text += text_block + "\n"
    except Exception:
        raise HTTPException(status_code=422, detail="Failed to parse structure. Target PDF may be malformed or password encrypted.")

    clean_text = sanitize_and_check_injection(extracted_raw_text).strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Document text extraction failed. Document contains zero parseable strings.")

    # 3. Grounded structural synthesis via Provider-Agnostic LLM Factory
    ai_prompt = f"""
    You are an expert enterprise HR compliance parsing agent.
    Extract structural data from the following resume text.
    Return values matching the schema instructions precisely.
    
    Resume Source Text:
    {clean_text}
    """
    try:
        structured_json = AIFactory.generate_structured_json(
            prompt=ai_prompt,
            response_schema=ResumeExtractionSchema
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External Model Provider failed to resolve text extraction loop: {str(e)}"
        )

    # 4. Multi-Tenant database persistence layer
    skills_str = " ".join(structured_json.skills)
    experience_str = " ".join(structured_json.experience)
    languages_str = " ".join(structured_json.languages)
    compilation_text = f"{structured_json.summary} {skills_str} {experience_str} {languages_str}"
    
    # Request coordinate vector footprint array from our agnostic AI factory
    candidate_vector = AIFactory.generate_embedding(compilation_text)
    
    new_candidate = Candidate(
        organization_id=current_user.organization_id,
        name=structured_json.name,
        email=structured_json.email,
        summary=structured_json.summary,
        skills=structured_json.skills,
        experience=structured_json.experience,
        education=structured_json.education,
        languages=structured_json.languages,
        embedding=candidate_vector 
    )
    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)
    return new_candidate

@router.get("/candidates", response_model=list[CandidateResponse])
def list_organization_candidates(
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Enforces cross-tenant multi-user protection filters automatically."""
    return db.query(Candidate).filter(Candidate.organization_id == current_user.organization_id).all()


@router.post("/{job_id}/match/{candidate_id}", response_model=SemanticMatchScoreResponse)
def evaluate_single_candidate_match(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Calculates vector similarity between pre-cached candidate and job description arrays."""
    return OptimizationMatcherService.evaluate_single_pair(
        job_id=job_id,
        candidate_id=candidate_id,
        org_id=current_user.organization_id,
        db=db
    )

@router.get("/{job_id}/matches", response_model=RankedMatchesResponse)
def get_ranked_talent_matches(
    job_id: uuid.UUID,
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Returns a sorted list of candidates ranked by semantic matrix coordinate matching scores."""
    return OptimizationMatcherService.rank_all_available_talent(
        job_id=job_id,
        org_id=current_user.organization_id,
        db=db
    )
    
@router.post("/jobs/{job_id}/candidates/{candidate_id}/evaluate", response_model=CandidateEvaluationResponse)
def compute_candidate_evidentiary_evaluation(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Triggers an automated, evidence-backed structural qualification analysis loop via LLM."""
    return CandidateEvaluationWorkflowService.process_evidentiary_evaluation(
        job_id=job_id,
        candidate_id=candidate_id,
        org_id=current_user.organization_id,
        db=db
    )

@router.get("/jobs/{job_id}/candidates/{candidate_id}/evaluation", response_model=CandidateEvaluationResponse)
def fetch_stored_candidate_evaluation(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves a pre-calculated professional verification matrix report while enforcing multi-tenant isolation gates."""
    return CandidateEvaluationWorkflowService.retrieve_stored_evaluation(
        job_id=job_id,
        candidate_id=candidate_id,
        org_id=current_user.organization_id,
        db=db
    )
    
@router.get("/jobs/{job_id}/candidates/{candidate_id}/match-summary", response_model=MatchSummaryResponse)
def get_candidate_human_match_summary(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Generates a highly scannable human-readable breakdown matrix of a candidate's qualification status."""
    return CandidateEvaluationWorkflowService.generate_human_match_summary(
        job_id=job_id,
        candidate_id=candidate_id,
        org_id=current_user.organization_id,
        db=db
    )
    
@router.post("/jobs/{job_id}/candidates/{candidate_id}/blind-evaluate", response_model=BlindEvaluationResponse)
def run_candidate_blind_evaluation_defended(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Strips private identity identifiers and neutralizes adversarial prompt injection script attempts."""
    audit_record = BlindEvaluationWorkflowService.process_blind_evaluation(
        job_id=job_id,
        candidate_id=candidate_id,
        org_id=current_user.organization_id,
        db=db
    )
    
    # Format database column fields to match schema response output structures
    return BlindEvaluationResponse(
        id=audit_record.id,
        candidate_id=audit_record.candidate_id,
        job_id=audit_record.job_id,
        organization_id=audit_record.organization_id,
        model_provider=audit_record.model_provider,
        estimated_cost=audit_record.estimated_cost,
        evaluation=BlindEvaluationResultSchema.model_validate(audit_record.evaluation_result),
        created_at=audit_record.created_at
    )