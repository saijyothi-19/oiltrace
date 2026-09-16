import pytest
from app.main import app

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

def test_system_status_endpoint(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["service"] == "OILTRACE Marine Decision Support API"

def test_seeded_admin_login(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@oiltrace.org", "password": "AdminPass2026!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@oiltrace.org"
    assert data["user"]["role"] == "ADMIN"

def test_auth_me_with_token(client):
    # Login first
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "analyst@oiltrace.org", "password": "AnalystPass2026!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Call /me
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "analyst@oiltrace.org"
    assert me_data["role"] == "ANALYST"

def test_invalid_login_error_format(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@oiltrace.org", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    err = response.json()
    assert "error" in err
    assert err["error"]["code"] == "UNAUTHORIZED"

import uuid

def test_user_registration_flow(client):
    new_email = f"new_investigator_{uuid.uuid4().hex[:8]}@oiltrace.org"
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "name": "New Investigator",
            "email": new_email,
            "password": "SecurePassword123!",
            "role": "ANALYST",
        },
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == new_email

    # Verify login works for newly registered user
    login_resp = client.post(
        "/api/auth/login",
        json={"email": new_email, "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()
