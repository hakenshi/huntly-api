import pytest
from fastapi.testclient import TestClient
from database.test_connection import get_test_db, create_test_tables, drop_test_tables
from database.connection import get_db
from main import app

# Override da dependência do banco
app.dependency_overrides[get_db] = get_test_db

@pytest.fixture
def client():
    create_test_tables()
    with TestClient(app) as c:
        yield c
    drop_test_tables()

def test_register_user(client):
    response = client.post("/auth/register", json={
        "email": "test@test.com",
        "password": "123456",
        "name": "Test User"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_register_duplicate_email(client):
    # Primeiro usuário
    client.post("/auth/register", json={
        "email": "test@test.com",
        "password": "123456",
        "name": "Test User"
    })
    
    # Tentar registrar mesmo email
    response = client.post("/auth/register", json={
        "email": "test@test.com",
        "password": "123456",
        "name": "Another User"
    })
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

def test_login_valid_user(client):
    # Registrar usuário
    client.post("/auth/register", json={
        "email": "test@test.com",
        "password": "123456",
        "name": "Test User"
    })
    
    # Login
    response = client.post("/auth/login", json={
        "email": "test@test.com",
        "password": "123456"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_login_invalid_credentials(client):
    response = client.post("/auth/login", json={
        "email": "wrong@test.com",
        "password": "wrongpass"
    })
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

def test_get_me_authenticated(client):
    # Registrar e fazer login
    register_response = client.post("/auth/register", json={
        "email": "test@test.com",
        "password": "123456",
        "name": "Test User"
    })
    token = register_response.json()["access_token"]
    
    # Acessar /me
    response = client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@test.com"
    assert data["name"] == "Test User"

def test_get_me_unauthenticated(client):
    response = client.get("/auth/me")
    assert response.status_code == 403
