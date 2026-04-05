# app/api/routes/users.py

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from fastapi.templating import Jinja2Templates

from app.db.database import get_db
from app.db.models import Transaction
from app.crud import transaction as crud_transaction

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


# ================= HELPER =================
def calculate_summary(transactions):
    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense
    }


# ================= LOGIN PAGE =================
@router.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# ================= LOGIN =================
@router.post("/login")
def login(request: Request, role: str = Form(...)):
    # ✅ store role in session
    request.session["role"] = role

    # ✅ force redirect cleanly (NO query params)
    response = RedirectResponse(url="/dashboard", status_code=303)
    return response


# ================= DASHBOARD =================
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    role = request.session.get("role")

    # ❌ If no role → back to login
    if not role:
        return RedirectResponse(url="/", status_code=303)

    transactions = db.query(Transaction).order_by(Transaction.date.desc()).all()

    summary = calculate_summary(transactions)

    category_breakdown = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label("total")
    ).group_by(Transaction.category).all()

    monthly_summary = db.query(
        func.strftime("%Y-%m", Transaction.date).label("month"),
        func.sum(Transaction.amount).label("total")
    ).group_by("month").all()

    return templates.TemplateResponse(
        "Dashboard.html",
        {
            "request": request,
            "role": role,
            "transactions": transactions,
            "summary": summary,
            "category_breakdown": category_breakdown,
            "monthly_summary": monthly_summary,
            "recent_transactions": transactions[:10]
        }
    )


# ================= CREATE =================
@router.post("/transactions/create")
def create_transaction(
    request: Request,
    amount: float = Form(...),
    type: str = Form(...),
    category: str = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    crud_transaction.create_transaction(
        db=db,
        amount=amount,
        type=type,
        category=category,
        date=datetime.strptime(date, "%Y-%m-%d").date(),
        notes=notes
    )

    return RedirectResponse(url="/dashboard", status_code=303)


# ================= EDIT =================
@router.get("/transactions/edit/{transaction_id}", response_class=HTMLResponse)
def edit_transaction_form(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    return templates.TemplateResponse(
        "EditTransaction.html",
        {"request": request, "transaction": transaction}
    )


@router.post("/transactions/edit/{transaction_id}")
def update_transaction(
    transaction_id: int,
    request: Request,
    amount: float = Form(...),
    type: str = Form(...),
    category: str = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    crud_transaction.update_transaction(
        db=db,
        transaction_id=transaction_id,
        amount=amount,
        type=type,
        category=category,
        date=datetime.strptime(date, "%Y-%m-%d").date(),
        notes=notes
    )

    return RedirectResponse(url="/dashboard", status_code=303)


# ================= DELETE =================
@router.post("/transactions/delete/{transaction_id}")
def delete_transaction(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

    crud_transaction.delete_transaction(db, transaction_id)

    return RedirectResponse(url="/dashboard", status_code=303)