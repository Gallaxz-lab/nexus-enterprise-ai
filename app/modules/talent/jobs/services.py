import io
import re
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from typing import List, Optional

from app.core.ai_factory.llm import AIFactory
from app.modules.talent.jobs.models import JobProfile
from app.modules.talent.jobs.schemas import JobProfileExtractionSchema, HybridSearchResponse, HybridSearchCandidateElement
from app.modules.talent.candidates.models import Candidate 

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB protection limit

class JobIngestionService:
    @staticmethod
    def parse_pdf_text(file: UploadFile) -> str:
        """Natively reads document binary streams using pypdf."""
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Unsupported media format. Only standard PDF documents are allowed.")
        
        contents = file.file.read()
        if len(contents) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="Document payload size limit exceeded (5MB maximum).")
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Cannot process blank or empty document binary payloads.")

        try:
            pdf_stream = io.BytesIO(contents)
            reader = PdfReader(pdf_stream)
            extracted_text = ""
            for page in reader.pages:
                text_block = page.extract_text()
                if text_block:
                    extracted_text += text_block + "\n"
            return extracted_text.strip()
        except Exception:
            raise HTTPException(status_code=422, detail="Failed to parse structure. Target PDF may be malformed.")

    @staticmethod
    def extract_and_store_profile(raw_text: str, org_id, db: Session) -> JobProfile:
        """Sends clean text into the AI pipeline and saves the validated profile result."""
        if not raw_text:
            raise HTTPException(status_code=400, detail="Document text extraction failed. Document contains zero parseable strings.")

        ai_prompt = f"""
        You are an expert enterprise HR compliance parsing agent.
        Analyze this Job Description document text and extract its structural profile.
        
        Job Description Text:
        {raw_text}
        """
        
        try:
            structured_json = AIFactory.generate_structured_json(
                prompt=ai_prompt,
                response_schema=JobProfileExtractionSchema
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"External Model Provider failed to resolve text extraction loop: {str(e)}"
            )
            
        req_skills = " ".join(structured_json.required_skills)
        pref_skills = " ".join(structured_json.preferred_skills)
        resp_str = " ".join(structured_json.responsibilities)
        tech_str = " ".join(structured_json.technologies)
        compilation_text = f"{structured_json.title} {structured_json.seniority} {req_skills} {pref_skills} {resp_str} {tech_str} {structured_json.required_experience}"
        
        job_vector = AIFactory.generate_embedding(compilation_text)

        new_job = JobProfile(
            organization_id=org_id,
            title=structured_json.title,
            seniority=structured_json.seniority,
            responsibilities=structured_json.responsibilities,
            required_skills=structured_json.required_skills,
            preferred_skills=structured_json.preferred_skills,
            required_experience=structured_json.required_experience,
            education=structured_json.education,
            technologies=structured_json.technologies,
            embedding=job_vector 
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        return new_job

class VectorMathService:
    @staticmethod
    def calculate_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Computes structural dot product relationships over target multidimensional arrays."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        magnitude_a = sum(a * a for a in vec_a) ** 0.5
        magnitude_b = sum(b * b for b in vec_b) ** 0.5
        
        if not magnitude_a or not magnitude_b:
            return 0.0
            
        # Return calculated structural data score rounded cleanly
        return round(dot_product / (magnitude_a * magnitude_b), 4)

class OptimizationMatcherService:
    @staticmethod
    def evaluate_single_pair(job_id: uuid.UUID, candidate_id: uuid.UUID, org_id: uuid.UUID, db: Session) -> dict:
        """Compares two pre-cached database vector elements while enforcing absolute tenant isolation bounds."""
        job = db.query(JobProfile).filter(JobProfile.id == job_id, JobProfile.organization_id == org_id).first()
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id, Candidate.organization_id == org_id).first()
        
        if not job or not candidate:
            raise HTTPException(status_code=404, detail="Target document identifiers not found or organization cross-access denied.")
            
        score = VectorMathService.calculate_cosine_similarity(job.embedding, candidate.embedding)
        return {"candidate_id": candidate.id, "job_id": job.id, "semantic_match_score": score}

    @staticmethod
    def rank_all_available_talent(job_id: uuid.UUID, org_id: uuid.UUID, db: Session) -> dict:
        """Retrieves and calculates ranked matches across all corporate candidates for a specific vacancy."""
        job = db.query(JobProfile).filter(JobProfile.id == job_id, JobProfile.organization_id == org_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Target vacancy profile tracking data not found.")
            
        candidates = db.query(Candidate).filter(Candidate.organization_id == org_id).all()
        
        results = []
        for c in candidates:
            # Bypass math processing loops smoothly if records lack coordinate mappings
            if not job.embedding or not c.embedding:
                score = 0.0
            else:
                score = VectorMathService.calculate_cosine_similarity(job.embedding, c.embedding)
                
            results.append({"candidate_id": c.id, "username": c.name or "Anonymous Profile Member", "semantic_match_score": score})
            
        # Sort values dynamically from highest similarity downwards
        results.sort(key=lambda x: x["semantic_match_score"], reverse=True)
        return {"job_id": job.id, "job_title": job.title, "ranked_matches": results}

class HybridSearchService:
    @staticmethod
    def execute_hybrid_sourcing(
        job_id: uuid.UUID,
        org_id: uuid.UUID,
        query: str,
        skills_filter: Optional[List[str]],
        seniority_filter: Optional[str],
        min_experience: Optional[int],
        tech_filter: Optional[List[str]],
        db: Session
    ) -> HybridSearchResponse:
        # 1. Verify Job Profile visibility limits
        job = db.query(JobProfile).filter(JobProfile.id == job_id, JobProfile.organization_id == org_id).first()
        if not job:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Target job description context record not found.")

        # 2. Build explicit database rule parameters dynamically
        query_builder = db.query(Candidate).filter(Candidate.organization_id == org_id)

        if seniority_filter:
            query_builder = query_builder.filter(Candidate.seniority.ilike(f"%{seniority_filter}%"))
        
        if min_experience is not None:
            query_builder = query_builder.filter(Candidate.years_experience >= min_experience)

        candidates = query_builder.all()
        
        # 3. Apply post-filtering criteria for array intersections
        filtered_candidates = []
        for c in candidates:
            # Check explicit skills overlap if specified
            if skills_filter:
                normalized_c_skills = [s.lower() for s in c.skills]
                if not any(sf.lower() in normalized_c_skills for sf in skills_filter):
                    continue
            
            # Check explicit technology overlap if specified
            if tech_filter:
                normalized_c_tech = [t.lower() for t in getattr(c, 'technologies', [])]
                if not any(tf.lower() in normalized_c_tech for tf in tech_filter):
                    continue
                    
            filtered_candidates.append(c)

        # 4. Compute dynamic query vector and rank matches
        query_vector = AIFactory.generate_embedding(query)
        from app.modules.talent.jobs.services import VectorMathService

        search_results = []
        for c in filtered_candidates:
            # A. Calculate Semantic Similarity Score (0.0 to 1.0)
            semantic_score = 0.0
            if query_vector and c.embedding:
                semantic_score = VectorMathService.calculate_cosine_similarity(query_vector, c.embedding)
                # Keep scores clamped inside a positive mathematical envelope
                semantic_score = max(0.0, min(1.0, semantic_score))

            # B. Calculate Explicit Skills Profile Intersection Score (0.0 to 1.0)
            skills_score = 0.0
            matched_skills = []
            if job.required_skills and c.skills:
                job_skills_set = {s.lower() for s in job.required_skills}
                cand_skills_set = {s.lower() for s in c.skills}
                intersection = job_skills_set.intersection(cand_skills_set)
                matched_skills = [s for s in c.skills if s.lower() in intersection]
                skills_score = len(intersection) / len(job_skills_set) if job_skills_set else 0.0

            # C. Synthesize Final Blended Hybrid Rank Score
            # Formula: 60% Conceptual Meaning Representation + 40% Explicit Technical Requirements
            final_score = round((semantic_score * 0.6) + (skills_score * 0.4), 4)

            search_results.append(HybridSearchCandidateElement(
                candidate_id=c.id,
                name=c.name or "Anonymous Sourcing Candidate",
                semantic_score=round(semantic_score, 4),
                skills_score=round(skills_score, 4),
                final_score=final_score,
                seniority=c.seniority,
                years_experience=c.years_experience or 0,
                matched_skills=matched_skills
            ))

        # Sort the final candidates list array by highest blended suitability rank
        search_results.sort(key=lambda x: x.final_score, reverse=True)
        return HybridSearchResponse(job_id=job_id, query=query, results=search_results)