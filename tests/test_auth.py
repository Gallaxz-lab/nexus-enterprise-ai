import pytest

def test_register_organization_success(test_client):
    response = test_client.post("/organizations", json={"name": "Cyberdyne Systems"})
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["name"] == "Cyberdyne Systems"

def test_register_user_success(test_client):
    org = test_client.post("/organizations", json={"name": "Umbrella Corp"}).json()
    response = test_client.post("/auth/users", json={
        "organization_id": org["id"],
        "username": "albert_w",
        "email": "wesker@umbrella.com",
        "password": "secure_t_virus",
        "role": "admin"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "albert_w"

def test_login_validation_success(test_client):
    org = test_client.post("/organizations", json={"name": "Weyland-Yutani"}).json()
    test_client.post("/auth/users", json={
        "organization_id": org["id"], "username": "ripley",
        "email": "ripley@weyland.com", "password": "nuke-it-from-orbit", "role": "member"
    })
    
    response = test_client.post("/auth/login", json={
        "username": "ripley", "password": "nuke-it-from-orbit"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_credentials(test_client):
    response = test_client.post("/auth/login", json={"username": "fake", "password": "wrongpassword"})
    assert response.status_code == 401

def test_protected_profile_denies_missing_token(test_client):
    response = test_client.get("/auth/me")
    assert response.status_code == 401

def test_admin_route_clearance_granted(test_client):
    org = test_client.post("/organizations", json={"name": "Stark Industries"}).json()
    test_client.post("/auth/users", json={
        "organization_id": org["id"], "username": "tony_s",
        "email": "tony@stark.com", "password": "jarvis-override-1", "role": "admin"
    })
    token = test_client.post("/auth/login", json={"username": "tony_s", "password": "jarvis-override-1"}).json()["access_token"]
    
    response = test_client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["clearance_granted"] is True


def test_admin_route_blocks_standard_member(test_client):
    org = test_client.post("/organizations", json={"name": "Oscorp Industries"}).json()
    test_client.post("/auth/users", json={
        "organization_id": org["id"], "username": "peter_p",
        "email": "parker@oscorp.com", "password": "midtown-high-science", "role": "member"
    })
    token = test_client.post("/auth/login", json={"username": "peter_p", "password": "midtown-high-science"}).json()["access_token"]
    
    response = test_client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
