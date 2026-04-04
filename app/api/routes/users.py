# app/api/routes/users.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import transaction as crud_transaction
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/Templates")

# Helper function to calculate summary
def calculate_summary(transactions):
    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    balance = total_income - total_expense
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance
    }

@router.get("/dashboard")
def dashboard(request: Request, role: str, db: Session = Depends(get_db)):
    # Fetch all transactions from the database
    transactions = crud_transaction.get_all_transactions(db)
    
    # Calculate summary
    summary = calculate_summary(transactions)
    
    # Pass everything to the template
    return templates.TemplateResponse("Dashboard.html", {
        "request": request,
        "summary": summary,
        "transactions": transactions,
        "role": role
    })