# app/api/routes/users.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.db.database import get_db
from app.crud import transaction as crud_transaction
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/Templates")


# ================= HELPER FUNCTIONS =================
def calculate_summary(transactions):
    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    balance = total_income - total_expense
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance
    }


# ================= DASHBOARD ROUTE =================
@router.get("/dashboard")
def dashboard(
    request: Request,
    role: str,
    type: str = None,
    category: str = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    # ================= FETCH AND FILTER TRANSACTIONS =================
    transactions_query = crud_transaction.get_transactions_query(db)

    # Apply filters dynamically
    if type:
        transactions_query = transactions_query.filter(crud_transaction.Transaction.type == type)
    if category:
        transactions_query = transactions_query.filter(crud_transaction.Transaction.category.ilike(f"%{category}%"))
    if start_date:
        transactions_query = transactions_query.filter(
            crud_transaction.Transaction.date >= datetime.strptime(start_date, "%Y-%m-%d").date()
        )
    if end_date:
        transactions_query = transactions_query.filter(
            crud_transaction.Transaction.date <= datetime.strptime(end_date, "%Y-%m-%d").date()
        )

    # Execute query
    transactions = transactions_query.order_by(crud_transaction.Transaction.date.desc()).all()

    # ================= SUMMARY =================
    total_income = db.query(func.sum(crud_transaction.Transaction.amount)).filter(
        crud_transaction.Transaction.type == "income"
    ).scalar() or 0
    total_expense = db.query(func.sum(crud_transaction.Transaction.amount)).filter(
        crud_transaction.Transaction.type == "expense"
    ).scalar() or 0
    balance = total_income - total_expense
    summary = {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance
    }

    # ================= CATEGORY BREAKDOWN =================
    category_breakdown = db.query(
        crud_transaction.Transaction.category,
        func.sum(crud_transaction.Transaction.amount).label("total")
    ).group_by(crud_transaction.Transaction.category).all()

    # ================= MONTHLY SUMMARY =================
    monthly_summary = db.query(
        func.strftime("%Y-%m", crud_transaction.Transaction.date).label("month"),
        func.sum(crud_transaction.Transaction.amount).label("total")
    ).group_by("month").all()

    # ================= RECENT TRANSACTIONS =================
    recent_transactions = transactions[:10]  # latest 10 transactions

    # ================= RETURN TEMPLATE =================
    return templates.TemplateResponse(
        "Dashboard.html",
        {
            "request": request,
            "role": role,
            "transactions": transactions,
            "summary": summary,
            "category_breakdown": category_breakdown,
            "monthly_summary": monthly_summary,
            "recent_transactions": recent_transactions
        }
    )