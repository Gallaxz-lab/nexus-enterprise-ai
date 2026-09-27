import pytest
import uuid
from unittest.mock import patch
from app.modules.talent.candidates.models import Candidate
from app.modules.talent.jobs.models import JobProfile
from app.modules.talent.candidates.schemas import CandidateEvaluationSchema, EvidentiaryRequirementElement

@pytest.fixture
def setup_evidentiary_test_matrix(test_client, db_session):
    org = test_client.post("/organizations", json={"name": "Weyland Sourcing Corporation"}).json()
    token = test_client.post("/auth/login", json={
        "username": test_client.post("/auth/users", json={
            "organization_id": org["id"], "username": "ellen_ripley",
            "email": "ripley@weyland.com", "password": "secure_password_1", "role": "admin"
        }).json()["username"], "password": "secure_password_1"
    }).json()["access_token"]
    org_id = uuid.UUID(org["id"])

    # 1. Inject the AI Engineer Target vacancy criteria
    job_ai = JobProfile(
        organization_id=org_id, title="AI Engineer", seniority="Senior",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Kubernetes"],
        preferred_skills=["LLM"], required_experience="3+ years Python experience", education="BSc"
    )
    db_session.add(job_ai)

    # 2. Inject Candidate A: Strong Match Profile
    cand_a = Candidate(
        organization_id=org_id, name="Candidate A", skills=["Python", "FastAPI", "PostgreSQL", "LLM"],
        experience=["Worked as a Senior Python backend developer for 4 years building FastAPI applications."], education=["BSc Computer Science"]
    )
    # 3. Inject Candidate B: Partial Match Profile
    cand_b = Candidate(
        organization_id=org_id, name="Candidate B", skills=["Python", "Django", "SQL"],
        experience=["Web development worker writing Python Django apps for 2 years."], education=["High School Diploma"]
    )
    # 4. Inject Candidate C: Wrong Specialization Profile
    cand_c = Candidate(
        organization_id=org_id, name="Candidate C", skills=["React", "TypeScript", "Next.js"],
        experience=["Frontend UI design developer crafting interface layouts for 3 years."], education=["BSc Graphic Design"]
    )
    # 5. Inject Candidate D: Indirect Microservices Profile
    cand_d = Candidate(
        organization_id=org_id, name="Candidate D", skills=["Java", "Spring Boot", "AWS"],
        experience=["Core backend engineer managing enterprise microservices computing architectures for 5 years."], education=["MSc Data Engineering"]
    )
    
    db_session.add_all([cand_a, cand_b, cand_c, cand_d])
    db_session.commit()

    return {
        "token": token, "job_id": str(job_ai.id),
        "cand_a": str(cand_a.id), "cand_b": str(cand_b.id), "cand_c": str(cand_c.id), "cand_d": str(cand_d.id)
    }

# --- Test Case 1: Strong Match Candidate A Verification ---
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_evaluation_strong_match_candidate(mock_llm, test_client, setup_evidentiary_test_matrix):
    mock_llm.return_value = CandidateEvaluationSchema(
        matched_required_skills=["Python", "FastAPI", "PostgreSQL"],
        missing_required_skills=["Kubernetes"],
        matched_preferred_skills=["LLM"],
        relevant_experience_highlights=["4 years building FastAPI applications"],
        education_match_explanation="Meets standard criteria with BSc.",
        experience_match_rating="meets_requirement",
        evidentiary_checks=[
            EvidentiaryRequirementElement(requirement_name="3+ years Python experience", status="satisfied", extracted_text_evidence="Senior Python backend developer for 4 years")
        ],
        explanation="Excellent core backend engineering skill match.", confidence=0.95
    )

    headers = {"Authorization": f"Bearer {setup_evidentiary_test_matrix['token']}"}
    url = f"/talent/jobs/{setup_evidentiary_test_matrix['job_id']}/candidates/{setup_evidentiary_test_matrix['cand_a']}/evaluate"
    
    response = test_client.post(url, headers=headers)
    assert response.status_code == 200
    assert response.json()["evaluation"]["experience_match_rating"] == "meets_requirement"

# --- Test Case 2: Partial Match Candidate B Verification ---
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_evaluation_partial_match_candidate(mock_llm, test_client, setup_evidentiary_test_matrix):
    mock_llm.return_value = CandidateEvaluationSchema(
        matched_required_skills=["Python"], missing_required_skills=["FastAPI", "PostgreSQL", "Kubernetes"],
        matched_preferred_skills=[], relevant_experience_highlights=["Python Django for 2 years"],
        education_match_explanation="Lacks BSc credential requirements.", experience_match_rating="partially_meets",
        evidentiary_checks=[
            EvidentiaryRequirementElement(requirement_name="3+ years Python experience", status="partially_satisfied", extracted_text_evidence="Python Django apps for 2 years")
        ],
        explanation="Candidate knows basic Python but falls below experience requirements.", confidence=0.75
    )

    headers = {"Authorization": f"Bearer {setup_evidentiary_test_matrix['token']}"}
    url = f"/talent/jobs/{setup_evidentiary_test_matrix['job_id']}/candidates/{setup_evidentiary_test_matrix['cand_b']}/evaluate"
    
    response = test_client.post(url, headers=headers)
    assert response.status_code == 200
    assert response.json()["evaluation"]["experience_match_rating"] == "partially_meets"

# --- Test Case 3: Missing Information Unconfirmed Check (Candidate C) ---
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_evaluation_unconfirmed_missing_information(mock_llm, test_client, setup_evidentiary_test_matrix):
    mock_llm.return_value = CandidateEvaluationSchema(
        matched_required_skills=[], missing_required_skills=["Python", "FastAPI", "PostgreSQL", "Kubernetes"],
        matched_preferred_skills=[], relevant_experience_highlights=[],
        education_match_explanation="Wrong discipline mapping.", experience_match_rating="does_not_meet",
        evidentiary_checks=[
            EvidentiaryRequirementElement(requirement_name="3+ years Python experience", status="not_evidenced", extracted_text_evidence=None)
        ],
        explanation="Candidate focus is purely frontend client interfaces. No core backend proof found.", confidence=0.90
    )

    headers = {"Authorization": f"Bearer {setup_evidentiary_test_matrix['token']}"}
    url = f"/talent/jobs/{setup_evidentiary_test_matrix['job_id']}/candidates/{setup_evidentiary_test_matrix['cand_c']}/evaluate"
    
    response = test_client.post(url, headers=headers)
    assert response.status_code == 200
    assert response.json()["evaluation"]["evidentiary_checks"][0]["status"] == "not_evidenced"

def test_generate_human_match_summary_success(test_client, setup_evidentiary_test_matrix, db_session):
    from app.modules.talent.candidates.models import Candidate
    import uuid

    # 1. Manually inject a pre-calculated evaluation matrix into our test candidate row
    candidate_uuid = uuid.UUID(setup_evidentiary_test_matrix["cand_a"])
    candidate = db_session.query(Candidate).filter(Candidate.id == candidate_uuid).first()
    
    candidate.evaluation_matrix = {
        "matched_required_skills": ["Python", "FastAPI", "PostgreSQL"],
        "missing_required_skills": ["Kubernetes"],
        "matched_preferred_skills": ["LLM"],
        "relevant_experience_highlights": ["Built backend systems"],
        "education_match_explanation": "BSc satisfies requirements.",
        "experience_match_rating": "meets_requirement",
        "evidentiary_checks": [
            {"requirement_name": "Kubernetes", "status": "not_evidenced", "extracted_text_evidence": None}
        ],
        "explanation": "Strong match for backend/AI application development.",
        "confidence": 0.95
    }
    db_session.commit()

    # 2. Query the presentation summary route
    headers = {"Authorization": f"Bearer {setup_evidentiary_test_matrix['token']}"}
    url = f"/talent/jobs/{setup_evidentiary_test_matrix['job_id']}/candidates/{setup_evidentiary_test_matrix['cand_a']}/match-summary"
    
    response = test_client.get(url, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["candidate_name"] == "Candidate A"
    assert data["required_skills_check"]["Python"] == "✓"
    assert data["required_skills_check"]["Kubernetes"] == "✗"
    assert data["preferred_skills_check"]["LLM"] == "✓"
    assert data["experience_status"] == "✓ Meets requirement"
    assert "Strong match for backend" in data["executive_summary"]