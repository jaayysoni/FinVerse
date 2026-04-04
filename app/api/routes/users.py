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


# 👉 Dashboard page
@router.get("/dashboard", tags=["User"])
def dashboard(request: Request, role: str = None, db: Session = Depends(get_db)):
    # Fetch all transactions from DB
    transactions = crud_transaction.get_all_transactions(db)
    
    # Render dashboard template
    return templates.TemplateResponse("Dashboard.html", {
        "request": request,
        "transactions": transactions,
        "role": role
    })