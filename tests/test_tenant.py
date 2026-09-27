import pytest

def test_tenant_isolation_boundaries(test_client):
    # Setup corporate tenant network A
    org_a = test_client.post("/organizations", json={"name": "League of Shadows"}).json()
    test_client.post("/auth/users", json={
        "organization_id": org_a["id"], "username": "bruce_w",
        "email": "bruce@wayne.com", "password": "gotham-protector-1", "role": "admin"
    })
    test_client.post("/auth/users", json={
        "organization_id": org_a["id"], "username": "alfred_p",
        "email": "alfred@wayne.com", "password": "master-bruce-care", "role": "member"
    })
    
    # Setup corporate tenant network B
    org_b = test_client.post("/organizations", json={"name": "LexCorp Systems"}).json()
    test_client.post("/auth/users", json={
        "organization_id": org_b["id"], "username": "lex_l",
        "email": "lex@lexcorp.com", "password": "kryptonite-matrix", "role": "admin"
    })
    
    # Authenticate as Admin user belonging to organization A
    token_a = test_client.post("/auth/login", json={"username": "bruce_w", "password": "gotham-protector-1"}).json()["access_token"]
    
    # Call data retrieval route
    response = test_client.get("/organizations/my-data", headers={"Authorization": f"Bearer {token_a}"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["access_granted_for_tenant_id"] == org_a["id"]
    
    # Verify corporate teammate profiles are visible
    usernames = [record["username"] for record in data["visible_organization_records"]]
    assert "bruce_w" in usernames
    assert "alfred_p" in usernames
    
    # Verify cross-tenant isolation works (LexCorp data must not leak into Organization A)
    assert "lex_l" not in usernames
