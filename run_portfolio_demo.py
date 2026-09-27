import json
import requests

BASE_URL = "http://localhost:8000"

def execute_portfolio_demo_verification():
    print("========== 1. CHECKING INFRASTRUCTURE HEALTH ==========")
    health = requests.get(f"{BASE_URL}/health").json()
    print(f"Health Status Counter: {health}\n")
    
    # Simulates an authenticated system user context bearer token sequence
    headers = {"Authorization": "Bearer DEVELOPER_PORTFOLIO_MOCK_TOKEN"}

    print("========== 2. EXECUTING NEXUS TALENT ENGINE ==========")
    talent_payload = {
        "job_description": "Senior Python Backend Engineer. Required: FastAPI, PostgreSQL.",
        "resume_text": "Jane Doe. 6 years Python backend developer engineering microservices over FastAPI and PostgreSQL."
    }
    # Calls your frozen match vector routing engine
    talent_res = requests.post(f"{BASE_URL}/talent/match", json=talent_payload, headers=headers).json()
    print(f"Matching Evaluation Output:\n{json.dumps(talent_res, indent=2)}\n")

    print("========== 3. EXECUTING NEXUS AUDIT SYSTEM ==========")
    # Evaluates transaction sets to instantly surface supply chain discrepancies
    audit_url = f"{BASE_URL}/audit/compare/00000000-0000-0000-0000-000000000001/00000000-0000-0000-0000-000000000002"
    audit_res = requests.post(audit_url, headers=headers)
    if audit_res.status_code == 200:
        print(f"LangGraph Reconciliation Loop Matrix:\n{json.dumps(audit_res.json(), indent=2)}\n")
    else:
        print(f"Reconciliation route hit. Status returned: {audit_res.status_code} (Requires baseline data matching entries)\n")

    print("========== 4. EXECUTING NEXUS SUPPORT PIPELINE ==========")
    support_payload = {"question": "What is the company's hardware return policy?"}
    support_res = requests.post(f"{BASE_URL}/support/ask", json=support_payload, headers=headers).json()
    print(f"Grounded RAG Answer Evaluation Matrix:\n{json.dumps(support_res, indent=2)}\n")

if __name__ == "__main__":
    try:
        execute_portfolio_demo_verification()
    except Exception as e:
        print(f"Verification loop halted: {str(e)}. Make sure your docker containers are live via 'docker-compose up'")
