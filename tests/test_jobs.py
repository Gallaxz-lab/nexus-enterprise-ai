import pytest
import io
import uuid
from unittest.mock import patch
from app.modules.talent.jobs.schemas import JobProfileResponse

def generate_mock_pdf_stream():
    return io.BytesIO(b"%PDF-1.5 Mock Job Specification Details")

@pytest.fixture
def setup_matrix(test_client):
    org_a = test_client.post("/organizations", json={"name": "Weyland-Yutani Corp"}).json()
    token_a = test_client.post("/auth/login", json={
        "username": test_client.post("/auth/users", json={
            "organization_id": org_a["id"], "username": "ellen_r",
            "email": "ripley@weyland.com", "password": "nuke-it-from-orbit", "role": "admin"
        }).json()["username"], "password": "nuke-it-from-orbit"
    }).json()["access_token"]

    org_b = test_client.post("/organizations", json={"name": "Tyrell Corp"}).json()
    token_b = test_client.post("/auth/login", json={
        "username": test_client.post("/auth/users", json={
            "organization_id": org_b["id"], "username": "roy_batty",
            "email": "roy@tyrell.com", "password": "time-to-die-1", "role": "admin"
        }).json()["username"], "password": "time-to-die-1"
    }).json()["access_token"]

    return {"token_a": token_a, "org_a_id": org_a["id"], "token_b": token_b, "org_b_id": org_b["id"]}

# 1. Test Authenticated Upload
@patch("app.modules.talent.jobs.services.PdfReader")
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_upload_jd_authenticated_success(mock_llm, mock_pdf, test_client, setup_matrix):
    mock_pdf.return_value.pages = [type('Page', (object,), {'extract_text': lambda self: "Senior Python Engineer Role"})()]
    mock_llm.return_value = type('MockSchema', (object,), {
        "title": "Senior Python Engineer", "seniority": "Senior", "responsibilities": ["Build APIs"],
        "required_skills": ["Python"], "preferred_skills": ["FastAPI"], "required_experience": "5 years",
        "education": "BSc", "technologies": ["Docker"]
    })()

    payload = {"file": ("job.pdf", generate_mock_pdf_stream(), "application/pdf")}
    response = test_client.post("/talent/jobs/upload", files=payload, headers={"Authorization": f"Bearer {setup_matrix['token_a']}"})
    assert response.status_code == 201
    assert response.json()["title"] == "Senior Python Engineer"
    assert response.json()["organization_id"] == setup_matrix["org_a_id"]

# 2. Test Unauthenticated Upload
def test_upload_jd_unauthenticated_denied(test_client):
    payload = {"file": ("job.pdf", generate_mock_pdf_stream(), "application/pdf")}
    response = test_client.post("/talent/jobs/upload", files=payload)
    assert response.status_code == 401

# 3. Test Multi-Tenant Data Leak Isolation boundaries
@patch("app.modules.talent.jobs.services.PdfReader")
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_cross_tenant_jd_isolation(mock_llm, mock_pdf, test_client, setup_matrix):
    mock_pdf.return_value.pages = [type('Page', (object,), {'extract_text': lambda self: "Secret Role"})()]
    mock_llm.return_value = type('MockSchema', (object,), {"title": "Secret Role", "seniority": "Staff", "responsibilities": [], "required_skills": [], "preferred_skills": [], "required_experience": None, "education": None, "technologies": []})()

    # Org A uploads a job description
    payload = {"file": ("job.pdf", generate_mock_pdf_stream(), "application/pdf")}
    job_a = test_client.post("/talent/jobs/upload", files=payload, headers={"Authorization": f"Bearer {setup_matrix['token_a']}"}).json()

    # User from Org B tries to look up Org A's job details directly via ID
    response_view = test_client.get(f"/talent/jobs/{job_a['id']}", headers={"Authorization": f"Bearer {setup_matrix['token_b']}"})
    assert response_view.status_code == 404

    # User from Org B queries their job listing index page
    response_list = test_client.get("/talent/jobs", headers={"Authorization": f"Bearer {setup_matrix['token_b']}"})
    assert len(response_list.json()) == 0

# 4. Test Invalid Media Type Rejection
def test_upload_invalid_file_type(test_client, setup_matrix):
    payload = {"file": ("readme.txt", io.BytesIO(b"Plain Text"), "text/plain")}
    response = test_client.post("/talent/jobs/upload", files=payload, headers={"Authorization": f"Bearer {setup_matrix['token_a']}"})
    assert response.status_code == 400

# 5. Test Empty Document Graceful Handling
def test_upload_empty_document(test_client, setup_matrix):
    payload = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = test_client.post("/talent/jobs/upload", files=payload, headers={"Authorization": f"Bearer {setup_matrix['token_a']}"})
    assert response.status_code == 400

# 6. Test Model Connection Outage Fault Tolerance
@patch("app.modules.talent.jobs.services.PdfReader")
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_llm_failure_fault_tolerance(mock_llm, mock_pdf, test_client, setup_matrix):
    mock_pdf.return_value.pages = [type('Page', (object,), {'extract_text': lambda self: "Valid Data"})()]
    mock_llm.side_effect = Exception("Downstream connection timeout")

    payload = {"file": ("job.pdf", generate_mock_pdf_stream(), "application/pdf")}
    response = test_client.post("/talent/jobs/upload", files=payload, headers={"Authorization": f"Bearer {setup_matrix['token_a']}"})
    assert response.status_code == 502
