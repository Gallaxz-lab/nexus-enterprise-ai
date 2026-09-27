from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException, Query
from sqlalchemy.orm import Session
import uuid
from typing import List, Optional

from app.core.database.connection import get_db
from app.core.dependencies import auth_deps
from app.core.database import models as core_models
from app.modules.talent.jobs.models import JobProfile
from app.modules.talent.jobs.schemas import JobProfileResponse, SemanticMatchScoreResponse, RankedMatchesResponse, HybridSearchResponse
from app.modules.talent.jobs.services import JobIngestionService, OptimizationMatcherService,  HybridSearchService



router = APIRouter(prefix="/talent/jobs", tags=["Talent Job Profiles"])

@router.post("/upload", response_model=JobProfileResponse, status_code=status.HTTP_201_CREATED)
async def upload_job_description(
    file: UploadFile = File(...),
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Securely uploads, extracts, and stores an unstructured job description PDF."""
    raw_text = JobIngestionService.parse_pdf_text(file)
    return JobIngestionService.extract_and_store_profile(raw_text, current_user.organization_id, db)

@router.get("", response_model=list[JobProfileResponse])
def get_all_organization_jobs(
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all active job vacancies belonging exclusively to the user's organization."""
    return db.query(JobProfile).filter(JobProfile.organization_id == current_user.organization_id).all()

@router.get("/{job_id}", response_model=JobProfileResponse)
def get_specific_job_profile(
    job_id: uuid.UUID,
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves a single job profile record while enforcing strict multi-tenant boundary checks."""
    job = db.query(JobProfile).filter(
        JobProfile.id == job_id,
        JobProfile.organization_id == current_user.organization_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Requested Job Profile record not found or access denied.")
    return job

@router.post("/{job_id}/match/{candidate_id}", response_model=SemanticMatchScoreResponse)
def evaluate_single_candidate_match(job_id: uuid.UUID, candidate_id: uuid.UUID, current_user: core_models.User = Depends(auth_deps.get_current_user), db: Session = Depends(get_db)):
    return OptimizationMatcherService.evaluate_single_pair(job_id=job_id, candidate_id=candidate_id, org_id=current_user.organization_id, db=db)

@router.get("/{job_id}/matches", response_model=RankedMatchesResponse)
def get_ranked_talent_matches(job_id: uuid.UUID, current_user: core_models.User = Depends(auth_deps.get_current_user), db: Session = Depends(get_db)):
    return OptimizationMatcherService.rank_all_available_talent(job_id=job_id, org_id=current_user.organization_id, db=db)

@router.get("/{job_id}/search", response_model=HybridSearchResponse)
def search_organization_candidates(
    job_id: uuid.UUID,
    query: str = Query(..., description="The conceptual search text string."),
    skills: Optional[List[str]] = Query(None, description="Explicit hard requirement skill tokens."),
    seniority: Optional[str] = Query(None, description="Explicit seniority text classification matching parameter."),
    years_experience: Optional[int] = Query(None, description="Minimum calendar years background threshold."),
    technologies: Optional[List[str]] = Query(None, description="Explicit technology stack token filter lists."),
    current_user: core_models.User = Depends(auth_deps.get_current_user),
    db: Session = Depends(get_db)
):
    """Executes a decoupled multi-tenant hybrid ranking search combining structural query rules and semantic footprints."""
    return HybridSearchService.execute_hybrid_sourcing(
        job_id=job_id,
        org_id=current_user.organization_id,
        query=query,
        skills_filter=skills,
        seniority_filter=seniority,
        min_experience=years_experience,
        tech_filter=technologies,
        db=db
    )