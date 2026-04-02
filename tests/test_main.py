"""
Integration tests covering authentication and role-based access control.

Run with:
    pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole

from sqlalchemy.pool import StaticPool

# Use an in-memory SQLite DB for tests — isolated per session
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Seed one user per role
    for role, email, pwd in [
        (UserRole.admin, "admin@test.com", "admin123"),
        (UserRole.analyst, "analyst@test.com", "analyst123"),
        (UserRole.viewer, "viewer@test.com", "viewer123"),
    ]:
        db.add(User(
            full_name=role.value.capitalize(),
            email=email,
            hashed_password=hash_password(pwd),
            role=role,
        ))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(setup_db):
    return TestClient(app)


def get_token(client, email, password):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── Auth tests ──────────────────────────────────────────────────────────────

class TestAuth:
    def test_login_success(self, client):
        resp = client.post("/auth/login", json={"email": "admin@test.com", "password": "admin123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        resp = client.post("/auth/login", json={"email": "admin@test.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/auth/login", json={"email": "nobody@test.com", "password": "x"})
        assert resp.status_code == 401

    def test_me_returns_current_user(self, client):
        token = get_token(client, "viewer@test.com", "viewer123")
        resp = client.get("/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == "viewer@test.com"

    def test_me_without_token_returns_403(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code in (401, 403)


# ── RBAC tests ──────────────────────────────────────────────────────────────

class TestRBAC:
    def test_viewer_cannot_create_transaction(self, client):
        token = get_token(client, "viewer@test.com", "viewer123")
        resp = client.post("/transactions/", headers=auth_headers(token), json={
            "amount": 100.0, "type": "income", "category": "salary", "date": "2025-01-01"
        })
        assert resp.status_code == 403

    def test_analyst_cannot_create_transaction(self, client):
        token = get_token(client, "analyst@test.com", "analyst123")
        resp = client.post("/transactions/", headers=auth_headers(token), json={
            "amount": 100.0, "type": "income", "category": "salary", "date": "2025-01-01"
        })
        assert resp.status_code == 403

    def test_admin_can_create_transaction(self, client):
        token = get_token(client, "admin@test.com", "admin123")
        resp = client.post("/transactions/", headers=auth_headers(token), json={
            "amount": 500.0, "type": "income", "category": "salary", "date": "2025-01-15"
        })
        assert resp.status_code == 201
        assert resp.json()["amount"] == 500.0

    def test_viewer_can_list_transactions(self, client):
        token = get_token(client, "viewer@test.com", "viewer123")
        resp = client.get("/transactions/", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_viewer_cannot_manage_users(self, client):
        token = get_token(client, "viewer@test.com", "viewer123")
        resp = client.get("/users/", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_admin_can_list_users(self, client):
        token = get_token(client, "admin@test.com", "admin123")
        resp = client.get("/users/", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_viewer_can_access_dashboard(self, client):
        token = get_token(client, "viewer@test.com", "viewer123")
        resp = client.get("/dashboard/summary", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_viewer_cannot_access_insights(self, client):
        token = get_token(client, "viewer@test.com", "viewer123")
        resp = client.get("/dashboard/insights", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_analyst_can_access_insights(self, client):
        token = get_token(client, "analyst@test.com", "analyst123")
        resp = client.get("/dashboard/insights", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "avg_transaction_amount" in data
        assert "top_income_categories" in data
        assert "weekly_trends" in data

    def test_admin_can_access_insights(self, client):
        token = get_token(client, "admin@test.com", "admin123")
        resp = client.get("/dashboard/insights", headers=auth_headers(token))
        assert resp.status_code == 200


# ── Transaction validation tests ─────────────────────────────────────────────

class TestTransactionValidation:
    def test_negative_amount_rejected(self, client):
        token = get_token(client, "admin@test.com", "admin123")
        resp = client.post("/transactions/", headers=auth_headers(token), json={
            "amount": -50.0, "type": "expense", "category": "rent", "date": "2025-01-01"
        })
        assert resp.status_code == 422

    def test_missing_required_fields_rejected(self, client):
        token = get_token(client, "admin@test.com", "admin123")
        resp = client.post("/transactions/", headers=auth_headers(token), json={
            "amount": 100.0
        })
        assert resp.status_code == 422

    def test_soft_delete_hides_record(self, client):
        token = get_token(client, "admin@test.com", "admin123")
        # Create
        create_resp = client.post("/transactions/", headers=auth_headers(token), json={
            "amount": 200.0, "type": "expense", "category": "groceries", "date": "2025-02-01"
        })
        tx_id = create_resp.json()["id"]
        # Delete
        client.delete(f"/transactions/{tx_id}", headers=auth_headers(token))
        # Fetch — should 404
        get_resp = client.get(f"/transactions/{tx_id}", headers=auth_headers(token))
        assert get_resp.status_code == 404

    def test_updated_at_changes_on_update(self, client):
        token = get_token(client, "admin@test.com", "admin123")
        create_resp = client.post("/transactions/", headers=auth_headers(token), json={
            "amount": 300.0, "type": "income", "category": "bonus", "date": "2025-03-01"
        })
        assert create_resp.status_code == 201
        tx = create_resp.json()
        original_updated_at = tx["updated_at"]

        import time
        time.sleep(0.05)

        patch_resp = client.patch(
            f"/transactions/{tx['id']}",
            headers=auth_headers(token),
            json={"amount": 350.0},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["updated_at"] != original_updated_at
