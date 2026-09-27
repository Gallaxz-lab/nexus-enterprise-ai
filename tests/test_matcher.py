import pytest
import uuid
from app.modules.talent.candidates.models import Candidate
from app.modules.talent.jobs.models import JobProfile
from app.core.ai_factory.llm import AIFactory

@pytest.fixture
def setup_symmetrical_test_matrix(test_client, db_session):
    # 1. Register corporate organization tenant gate and user session context
    org = test_client.post("/organizations", json={"name": "Nexus Sourcing Labs"}).json()
    token = test_client.post("/auth/login", json={
        "username": test_client.post("/auth/users", json={
            "organization_id": org["id"], "username": "sourcing_lead",
            "email": "lead@nexus.com", "password": "secure_sourcing_1", "role": "admin"
        }).json()["username"], "password": "secure_sourcing_1"
    }).json()["access_token"]
    
    org_id = uuid.UUID(org["id"])

    # 2. Inject 5 highly tuned candidate string footprints for local mock similarity loops
    candidates = [
        {
            "name": "Candidate A", 
            "text": "API Backend Developer Python FastAPI PostgreSQL server cloud configuration architecture systems engineering",
            "skills": ["Python", "FastAPI", "PostgreSQL"], "summary": "Core backend engineering lead specialized in microservices."
        },
        {
            "name": "Candidate B", 
            "text": "Java Spring Boot enterprise microservices cloud compute transaction processing databases systems management",
            "skills": ["Java", "Spring Boot"], "summary": "Enterprise engineer focused on scalable cloud business logic paths."
        },
        {
            "name": "Candidate C", 
            "text": "Frontend Client Interface UI UX layouts dashboards design views",
            "skills": ["React", "TypeScript"], "summary": "Frontend developer styling web components."
        },
        {
            "name": "Candidate D", 
            "text": "AI Engineer Machine Learning Neural Networks Deep Learning NLP LLMs GenAI Models Data Science Analytics",
            "skills": ["Python", "Machine Learning", "LLM"], "summary": "AI research specialist building intelligent model agents."
        },
        {
            "name": "Candidate E", 
            "text": "Reporting spreadsheets presentation sheets business charting numbers logs",
            "skills": ["SQL", "Tableau"], "summary": "Data reporting clerk analyzing business matrix tables."
        }
    ]
    
    for c in candidates:
        # Generate raw embedding vector directly using the distinct text signatures
        vector = AIFactory.generate_embedding(c["text"])
        db_session.add(Candidate(
            organization_id=org_id,
            name=c["name"],
            summary=c["summary"],
            skills=c["skills"],
            experience=[c["text"]],
            education=["BSc Computer Science"],
            embedding=vector
        ))

    # 3. Inject 2 distinct job specifications matching the candidate text strings exactly
    # Job 1: AI Engineer
    ai_job_text = "AI Engineer Machine Learning Neural Networks Deep Learning NLP LLMs GenAI Models Data Science Analytics"
    job_ai = JobProfile(
        organization_id=org_id, title="AI Engineer",
        required_skills=["Python", "LLM"], embedding=AIFactory.generate_embedding(ai_job_text)
    )
    
    # Job 2: Backend Developer
    backend_job_text = "API Backend Developer Python FastAPI PostgreSQL server cloud configuration architecture systems engineering"
    job_backend = JobProfile(
        organization_id=org_id, title="Backend Developer",
        required_skills=["Python", "FastAPI"], embedding=AIFactory.generate_embedding(backend_job_text)
    )
    
    db_session.add(job_ai)
    db_session.add(job_backend)
    db_session.commit()

    return {
        "token": token,
        "job_ai_id": str(job_ai.id),
        "job_backend_id": str(job_backend.id)
    }

def test_semantic_match_ranking_ai_engineer(test_client, setup_symmetrical_test_matrix):
    """Validates that the AI Engineer vacancy ranks machine learning candidates at the top."""
    headers = {"Authorization": f"Bearer {setup_symmetrical_test_matrix['token']}"}
    response = test_client.get(f"/talent/jobs/{setup_symmetrical_test_matrix['job_ai_id']}/matches", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    ranked_names = [item["username"] for item in data["ranked_matches"]]
    
    assert "Candidate D" in ranked_names
    assert "Candidate C" in ranked_names
    assert ranked_names.index("Candidate D") < ranked_names.index("Candidate C")

def test_semantic_match_ranking_backend_developer(test_client, setup_symmetrical_test_matrix):
    """Validates that the Backend Developer vacancy ranks FastAPI candidates at the top."""
    headers = {"Authorization": f"Bearer {setup_symmetrical_test_matrix['token']}"}
    response = test_client.get(f"/talent/jobs/{setup_symmetrical_test_matrix['job_backend_id']}/matches", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    ranked_names = [item["username"] for item in data["ranked_matches"]]
    
    assert "Candidate A" in ranked_names
    assert "Candidate C" in ranked_names
    assert ranked_names.index("Candidate A") < ranked_names.index("Candidate C")
