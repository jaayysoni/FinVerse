from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import transaction as crud_transaction

router = APIRouter()
templates = Jinja2Templates(directory="app/Templates")


# 👉 Login page
@router.get("/", tags=["User"])
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# 👉 Handle login form
@router.post("/login", tags=["User"])
def login(role: str = Form(...)):
    # Redirect to dashboard with role info
    return RedirectResponse(url=f"/dashboard?role={role}", status_code=303)


# 👉 Dashboard page with dummy + real DB data
@router.get("/dashboard", tags=["User"])
def dashboard(request: Request, role: str = None, db: Session = Depends(get_db)):
    # ✅ Fetch real transactions from DB
    transactions = crud_transaction.get_all_transactions(db)

    # ===== Dummy summary for UI rendering =====
    summary = {
        "total_income": sum(t.amount for t in transactions if t.type == "income") or 0,
        "total_expense": sum(t.amount for t in transactions if t.type == "expense") or 0,
        "balance": sum(t.amount if t.type == "income" else -t.amount for t in transactions) or 0
    }

    # ===== Dummy analytics data =====
    category_breakdown = [
        {"category": "Salary", "total": 5000},
        {"category": "Freelance", "total": 1200},
        {"category": "Groceries", "total": 200},
        {"category": "Transport", "total": 150},
        {"category": "Entertainment", "total": 300},
    ]

    monthly_summary = [
        {"month": "April 2026", "total": 6200},
        {"month": "March 2026", "total": 4000},
    ]

    recent_transactions = transactions[-3:] if transactions else []

    # ===== Render Dashboard with all data =====
    return templates.TemplateResponse("Dashboard.html", {
        "request": request,
        "role": role or "admin",
        "summary": summary,
        "transactions": transactions,
        "category_breakdown": category_breakdown,
        "monthly_summary": monthly_summary,
        "recent_transactions": recent_transactions
    })