from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ============================================================
# 🔧 HELPERS
# ============================================================

def login_admin():
    """Login as admin user for authenticated routes"""
    response = client.post("/login", data={"role": "admin"})
    assert response.status_code in [200, 303]


def create_sample_transaction():
    """Create and return a sample transaction ID"""
    login_admin()

    response = client.post("/api/transactions", json={
        "amount": 100,
        "type": "income",
        "category": "salary",
        "date": "2024-01-01",
        "notes": "sample"
    })

    assert response.status_code == 201
    return response.json()["id"]


# ============================================================
# 🟢 1. APP HEALTH
# ============================================================

def test_app_runs():
    response = client.get("/")
    assert response.status_code == 200


# ============================================================
# 🟢 2. TRANSACTION CRUD (API)
# ============================================================

def test_create_transaction():
    login_admin()

    response = client.post("/api/transactions", json={
        "amount": 120,
        "type": "income",
        "category": "freelance",
        "date": "2024-01-02",
        "notes": "test create"
    })

    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert isinstance(data["id"], int)


def test_get_transaction():
    txn_id = create_sample_transaction()

    response = client.get(f"/api/transactions/{txn_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == txn_id


def test_update_transaction():
    txn_id = create_sample_transaction()

    response = client.put(f"/api/transactions/{txn_id}", json={
        "amount": 150,
        "type": "income",
        "category": "salary",
        "date": "2024-01-01",
        "notes": "updated"
    })

    assert response.status_code == 200

    updated = client.get(f"/api/transactions/{txn_id}").json()
    assert updated["amount"] == 150
    assert updated["notes"] == "updated"


def test_delete_transaction():
    txn_id = create_sample_transaction()

    response = client.delete(f"/api/transactions/{txn_id}")
    assert response.status_code == 200

    # Ensure it's actually deleted
    check = client.get(f"/api/transactions/{txn_id}")
    assert check.status_code == 404


# ============================================================
# 🔴 3. VALIDATION & EDGE CASES
# ============================================================

def test_negative_amount():
    login_admin()

    response = client.post("/api/transactions", json={
        "amount": -100,
        "type": "income",
        "category": "salary",
        "date": "2024-01-01",
        "notes": ""
    })

    assert response.status_code == 422


def test_missing_fields():
    login_admin()

    response = client.post("/api/transactions", json={
        "amount": 100
    })

    assert response.status_code == 422


def test_invalid_type():
    login_admin()

    response = client.post("/api/transactions", json={
        "amount": 100,
        "type": "invalid_type",
        "category": "test",
        "date": "2024-01-01",
        "notes": ""
    })

    assert response.status_code == 422


# ============================================================
# 🟡 4. DASHBOARD (UI ROUTE)
# ============================================================

def test_dashboard_page():
    login_admin()

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


# ============================================================
# 🔵 5. ANALYTICS / SUMMARY API
# ============================================================

def test_summary_api():
    login_admin()

    response = client.get("/api/summary")
    assert response.status_code == 200

    data = response.json()

    assert "total_income" in data
    assert "total_expense" in data
    assert "balance" in data

    assert isinstance(data["total_income"], (int, float))
    assert isinstance(data["total_expense"], (int, float))
    assert isinstance(data["balance"], (int, float))