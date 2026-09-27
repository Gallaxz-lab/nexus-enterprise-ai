import pytest
import io
from unittest.mock import patch
from app.core.auth import security
from app.modules.talent.candidates.schemas import ResumeExtractionSchema

def generate_mock_pdf(pages=1, text="Standard Resume Content Text"):
    """Generates simple mock memory byte streams mimicking basic PDF footprints."""
    # For testing, we use standard bytes. In integration tests, we patch PdfReader to return strings.
    return io.BytesIO(b"%PDF-1.4 mock pdf structure bytes data streams")

@pytest.fixture
def test_setup_matrix(test_client):
    """Helper fixture setup registering Org A and Org B authentication states."""
    org_a = test_client.post("/organizations", json={"name": "Cyberdyne Systems"}).json()
    user_a = test_client.post("/auth/users", json={
        "organization_id": org_a["id"], "username": "sarah_c",
        "email": "sarah@cyberdyne.com", "password": "no-fate-but-what-we-make", "role": "admin"
    }).json()
    token_a = test_client.post("/auth/login", json={"username": "sarah_c", "password": "no-fate-but-what-we-make"}).json()["access_token"]

    org_b = test_client.post("/organizations", json={"name": "Umbrella Corporation"}).json()
    user_b = test_client.post("/auth/users", json={
        "organization_id": org_b["id"], "username": "albert_w",
        "email": "wesker@umbrella.com", "password": "complete-global-saturation", "role": "admin"
    }).json()
    token_b = test_client.post("/auth/login", json={"username": "albert_w", "password": "complete-global-saturation"}).json()["access_token"]

    return {
        "token_a": token_a, "org_a_id": org_a["id"],
        "token_b": token_b, "org_b_id": org_b["id"]
    }

# --- 1. Test Valid PDF Pipeline Execution ---
@patch("app.modules.talent.candidates.router.PdfReader")
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_upload_valid_pdf_success(mock_llm, mock_pdf, test_client, test_setup_matrix):
    mock_pdf.return_value.pages = [type('Page', (object,), {'extract_text': lambda self: "John Doe\nPython Developer"})()]
    mock_llm.return_value = ResumeExtractionSchema(name="John Doe", skills=["Python"])
    
    file_payload = {"file": ("resume.pdf", generate_mock_pdf(), "application/pdf")}
    headers = {"Authorization": f"Bearer {test_setup_matrix['token_a']}"}
    
    response = test_client.post("/talent/upload-resume", files=file_payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["name"] == "John Doe"
    assert "Python" in response.json()["skills"]

# --- 2. Test Multi-Page Processing Support ---
@patch("app.modules.talent.candidates.router.PdfReader")
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_upload_multi_page_pdf(mock_llm, mock_pdf, test_client, test_setup_matrix):
    page1 = type('Page', (object,), {'extract_text': lambda self: "Page One Profile"})()
    page2 = type('Page', (object,), {'extract_text': lambda self: "Page Two Operations"})()
    mock_pdf.return_value.pages = [page1, page2]
    mock_llm.return_value = ResumeExtractionSchema(summary="Extracted content over multiple pages")

    file_payload = {"file": ("resume.pdf", generate_mock_pdf(), "application/pdf")}
    headers = {"Authorization": f"Bearer {test_setup_matrix['token_a']}"}
    
    response = test_client.post("/talent/upload-resume", files=file_payload, headers=headers)
    assert response.status_code == 201

# --- 3. Test Invalid Media Type Rejection ---
def test_upload_invalid_file_type(test_client, test_setup_matrix):
    file_payload = {"file": ("malicious_script.sh", io.BytesIO(b"echo 'hack'"), "text/x-shellscript")}
    headers = {"Authorization": f"Bearer {test_setup_matrix['token_a']}"}
    
    response = test_client.post("/talent/upload-resume", files=file_payload, headers=headers)
    assert response.status_code == 400
    assert "Unsupported media format" in response.json()["detail"]

# --- 4. Test Empty Payloads Block ---
def test_upload_empty_document(test_client, test_setup_matrix):
    file_payload = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    headers = {"Authorization": f"Bearer {test_setup_matrix['token_a']}"}
    
    response = test_client.post("/talent/upload-resume", files=file_payload, headers=headers)
    assert response.status_code == 400

# --- 5. Test Missing Profile Resilience ---
@patch("app.modules.talent.candidates.router.PdfReader")
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_upload_missing_candidate_info(mock_llm, mock_pdf, test_client, test_setup_matrix):
    mock_pdf.return_value.pages = [type('Page', (object,), {'extract_text': lambda self: "Anonymous string content profile lines"})()]
    # Return schema populated entirely with fallback default structures
    mock_llm.return_value = ResumeExtractionSchema(name=None, email=None, skills=[])

    file_payload = {"file": ("anon.pdf", generate_mock_pdf(), "application/pdf")}
    headers = {"Authorization": f"Bearer {test_setup_matrix['token_a']}"}
    
    response = test_client.post("/talent/upload-resume", files=file_payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["name"] is None

# --- 6. Test LLM Connection Failure Isolation ---
@patch("app.modules.talent.candidates.router.PdfReader")
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_upload_llm_failure_handling(mock_llm, mock_pdf, test_client, test_setup_matrix):
    mock_pdf.return_value.pages = [type('Page', (object,), {'extract_text': lambda self: "John Doe Resume Text Data"})()]
    mock_llm.side_effect = Exception("OpenAI API rate limit or validation key failure.")

    file_payload = {"file": ("resume.pdf", generate_mock_pdf(), "application/pdf")}
    headers = {"Authorization": f"Bearer {test_setup_matrix['token_a']}"}
    
    response = test_client.post("/talent/upload-resume", files=file_payload, headers=headers)
    assert response.status_code == 502
    assert "External Model Provider failed" in response.json()["detail"]

# --- 7. Test Unauthorized Block Gates ---
def test_upload_unauthorized_token_missing(test_client):
    file_payload = {"file": ("resume.pdf", generate_mock_pdf(), "application/pdf")}
    response = test_client.post("/talent/upload-resume", files=file_payload)
    assert response.status_code == 401

# --- 8. Test Absolute Multi-Tenant Tenant Isolation ---
@patch("app.modules.talent.candidates.router.PdfReader")
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_cross_tenant_isolation_protection(mock_llm, mock_pdf, test_client, test_setup_matrix):
    mock_pdf.return_value.pages = [type('Page', (object,), {'extract_text': lambda self: "John Doe Resume Text Data"})()]
    mock_llm.return_value = ResumeExtractionSchema(name="John Tenant Worker", skills=["Security Auditing"])

    # 1. Upload file using Organization A credentials
    file_payload = {"file": ("resume.pdf", generate_mock_pdf(), "application/pdf")}
    test_client.post("/talent/upload-resume", files=file_payload, headers={"Authorization": f"Bearer {test_setup_matrix['token_a']}"})

    # 2. Query candidates endpoint using Organization B credentials
    headers_b = {"Authorization": f"Bearer {test_setup_matrix['token_b']}"}
    response_b = test_client.get("/talent/candidates", headers=headers_b)
    
    # 3. Assert total data separation: Organization B must get an empty candidate list back
    assert response_b.status_code == 200
    assert len(response_b.json()) == 0
