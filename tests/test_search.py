import pytest
import uuid
from app.modules.talent.candidates.models import Candidate
from app.modules.talent.jobs.models import JobProfile
from app.core.ai_factory.llm import AIFactory

@pytest.fixture
def setup_hybrid_search_matrix(test_client, db_session):
    # 1. Setup multi-tenant workspace partitions
    org_a = test_client.post("/organizations", json={"name": "Alpha Corporate Holdings"}).json()
    token_a = test_client.post("/auth/login", json={
        "username": test_client.post("/auth/users", json={
            "organization_id": org_a["id"], "username": "recruiter_a",
            "email": "a@alpha.com", "password": "secure_password_a", "role": "admin"
        }).json()["username"], "password": "secure_password_a"
    }).json()["access_token"]
    org_a_uuid = uuid.UUID(org_a["id"])

    org_b = test_client.post("/organizations", json={"name": "Beta Digital Group"}).json()
    token_b = test_client.post("/auth/login", json={
        "username": test_client.post("/auth/users", json={
            "organization_id": org_b["id"], "username": "recruiter_b",
            "email": "b@beta.com", "password": "secure_password_b", "role": "admin"
        }).json()["username"], "password": "secure_password_b"
    }).json()["access_token"]
    org_b_uuid = uuid.UUID(org_b["id"])

    # 2. Inject 10 mock candidates under Organization A partition space
    candidates_pool = [
        {"name": "Cand 1", "sen": "Senior", "exp": 7, "skills": ["Python", "FastAPI", "PostgreSQL"], "tech": ["Docker", "AWS"], "bio": "Senior Python Backend Developer crafting scalable FastAPI service tiers with PostgreSQL database logic handles data."},
        {"name": "Cand 2", "sen": "Junior", "exp": 1, "skills": ["Python", "FastAPI"], "tech": ["Docker"], "bio": "Junior web developer parsing simple Python scripts learning core FastAPI endpoints and application layouts."},
        {"name": "Cand 3", "sen": "Senior", "exp": 8, "skills": ["Python", "Machine Learning", "LLM"], "tech": ["PyTorch", "HuggingFace"], "bio": "Senior AI Infrastructure Engineer research specialist fine-tuning dense transformer models and vector space frameworks."},
        {"name": "Cand 4", "sen": "Mid", "exp": 4, "skills": ["Python", "Machine Learning"], "tech": ["TensorFlow"], "bio": "Machine Learning Engineer specialized in neural networks predictive algorithms optimization automation loops."},
        {"name": "Cand 5", "sen": "Senior", "exp": 6, "skills": ["React", "TypeScript", "Tailwind"], "tech": ["NextJS", "Vercel"], "bio": "Senior Frontend Engineer designing beautiful responsive component interfaces UI layouts using React TypeScript systems."},
        {"name": "Cand 6", "sen": "Junior", "exp": 2, "skills": ["React", "JavaScript"], "tech": ["CSS"], "bio": "Junior client developer building simple responsive web views template forms interactive styling hooks."},
        {"name": "Cand 7", "sen": "Senior", "exp": 5, "skills": ["SQL", "Tableau", "Excel"], "tech": ["Snowflake"], "bio": "Senior Data Analyst compiling business intelligence reports creating reporting dashboard matrices metrics warehousing lines."},
        {"name": "Cand 8", "sen": "Mid", "exp": 3, "skills": ["SQL", "Python", "Pandas"], "tech": ["PostgreSQL"], "bio": "Data Scientist processing massive structured log sets executing pipeline data clearing script operations analytics."},
        {"name": "Cand 9", "sen": "Senior", "exp": 9, "skills": ["Java", "Spring Boot", "Kafka"], "tech": ["Kubernetes", "Google Cloud"], "bio": "Senior Core Distributed Systems Architect designing backend high-volume banking engines with Java Spring Boot frameworks."},
        {"name": "Cand 10", "sen": "Mid", "exp": 3, "skills": ["Java", "Spring Boot"], "tech": ["Docker"], "bio": "Backend microservices engineer deploying modular web logic controllers inside isolated software environments systems."}
    ]

    for index, c in enumerate(candidates_pool):
        # Normal production string compilation pattern signature mapping
        comp_str = f"{c['bio']} {' '.join(c['skills'])} {' '.join(c['tech'])} {c['sen']}"
        vector = AIFactory.generate_embedding(comp_str)
        
        # Inject candidates into Org A's partition space
        db_session.add(Candidate(
            organization_id=org_a_uuid, name=c["name"], seniority=c["sen"],
            years_experience=c["exp"], skills=c["skills"], technologies=c["tech"],
            embedding=vector
        ))
        
        # Inject one copy profile under Org B partition space to test leak boundaries
        if index == 0:
            db_session.add(Candidate(
                organization_id=org_b_uuid, name="Org B Hidden Candidate", seniority=c["sen"],
                years_experience=c["exp"], skills=c["skills"], technologies=c["tech"],
                embedding=vector
            ))

    # 3. Inject 3 explicit Job Description vector matrices into Org A partition space
    job_backend = JobProfile(organization_id=org_a_uuid, title="Backend Developer", required_skills=["Python", "FastAPI"], embedding=AIFactory.generate_embedding("Backend Developer Python FastAPI PostgreSQL server APIs"))
    job_ai = JobProfile(organization_id=org_a_uuid, title="AI Engineer", required_skills=["Python", "LLM"], embedding=AIFactory.generate_embedding("AI Engineer Machine Learning Neural Networks Deep Learning NLP LLMs GenAI Models"))
    job_frontend = JobProfile(organization_id=org_a_uuid, title="Frontend Developer", required_skills=["React", "TypeScript"], embedding=AIFactory.generate_embedding("Frontend Developer React TypeScript Tailwind CSS design UI UX components views"))
    
    db_session.add(job_backend)
    db_session.add(job_ai)
    db_session.add(job_frontend)
    db_session.commit()

    return {
        "token_a": token_a, "token_b": token_b,
        "job_backend_id": str(job_backend.id), "job_ai_id": str(job_ai.id), "job_frontend_id": str(job_frontend.id)
    }

def test_hybrid_search_backend_success(test_client, setup_hybrid_search_matrix):
    """Validates that a backend developer query surfaces Python/FastAPI profiles at the top."""
    headers = {"Authorization": f"Bearer {setup_hybrid_search_matrix['token_a']}"}
    url = f"/talent/jobs/{setup_hybrid_search_matrix['job_backend_id']}/search?query=Python backend developer"
    
    response = test_client.get(url, headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # Assert high-signal profiles rise above frontend profiles in suitability ranking
    ranked_names = [item["name"] for item in data["results"]]
    assert ranked_names.index("Cand 1") < ranked_names.index("Cand 5")

def test_hybrid_search_ai_engineer_success(test_client, setup_hybrid_search_matrix):
    """Validates that an AI query surfaces transformer/LLM engineer profiles at the top."""
    headers = {"Authorization": f"Bearer {setup_hybrid_search_matrix['token_a']}"}
    url = f"/talent/jobs/{setup_hybrid_search_matrix['job_ai_id']}/search?query=AI engineer with LLM experience"
    
    response = test_client.get(url, headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    ranked_names = [item["name"] for item in data["results"]]
    assert ranked_names.index("Cand 3") < ranked_names.index("Cand 9")

def test_hybrid_search_with_explicit_filters(test_client, setup_hybrid_search_matrix):
    """Validates that database filter parameters discard profiles that do not match structural specifications."""
    headers = {"Authorization": f"Bearer {setup_hybrid_search_matrix['token_a']}"}
    
    # Find candidates with Python, at least 5 years experience, and Senior seniority
    url = f"/talent/jobs/{setup_hybrid_search_matrix['job_backend_id']}/search?query=Backend&skills=Python&seniority=Senior&years_experience=5"
    
    response = test_client.get(url, headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # Junior profiles like Cand 2 (1 yr exp) must be completely excluded by the rule guard filter
    for record in data["results"]:
        assert record["years_experience"] >= 5
        assert record["seniority"] == "Senior"
        assert record["name"] != "Cand 2"

def test_hybrid_search_tenant_data_isolation(test_client, setup_hybrid_search_matrix):
    """Validates that search operations are completely isolated between organizations."""
    headers_b = {"Authorization": f"Bearer {setup_hybrid_search_matrix['token_b']}"}
    
    # Org B recruiter attempts to search inside Org A's job description context link
    url = f"/talent/jobs/{setup_hybrid_search_matrix['job_backend_id']}/search?query=Python"
    
    response = test_client.get(url, headers=headers_b)
    # The platform blocks cross-tenant lookups with a 404 Not Found error
    assert response.status_code == 404
