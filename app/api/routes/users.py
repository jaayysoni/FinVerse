from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, date
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from fastapi.responses import Response
import csv
import io

from app.db.database import get_db
from app.db.models import Transaction

router = APIRouter()
templates = Jinja2Templates(directory="app/Templates")

VALID_ROLES = ["admin", "analyst", "viewer"]


# ================= SCHEMA =================
class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    type: str
    category: str
    date: date
    notes: str = ""

    @validator("type")
    def validate_type(cls, v):
        if v not in ["income", "expense"]:
            raise ValueError("Type must be 'income' or 'expense'")
        return v


# ================= RBAC =================
def get_role(request: Request):
    role = request.session.get("role")
    if not role:
        raise HTTPException(status_code=401)

    if role not in VALID_ROLES:
        raise HTTPException(status_code=403)

    return role


# ================= HELPERS =================
def calculate_summary(transactions):
    income = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")

    return {
        "total_income": income,
        "total_expense": expense,
        "balance": income - expense
    }


# ================= LOGIN =================
@router.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(request: Request, role: str = Form(...)):
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400)

    request.session["role"] = role
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


# ================= DASHBOARD (FIXED) =================
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    type: str = Query(None),
    category: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    search: str = Query(None),
):
    role = get_role(request)

    query = db.query(Transaction)

    # ✅ Filters (so UI works)
    if type:
        query = query.filter(Transaction.type == type)

    if category:
        query = query.filter(Transaction.category.ilike(f"%{category}%"))

    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, "%Y-%m-%d"))

    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, "%Y-%m-%d"))

    if search:
        query = query.filter(
            or_(
                Transaction.category.ilike(f"%{search}%"),
                Transaction.notes.ilike(f"%{search}%")
            )
        )

    transactions = query.order_by(Transaction.date.desc()).all()

    # ✅ Analytics
    category_data = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label("total")
    ).group_by(Transaction.category).all()

    monthly_data = db.query(
        func.strftime("%Y-%m", Transaction.date).label("month"),
        func.sum(Transaction.amount).label("total")
    ).group_by("month").all()

    return templates.TemplateResponse(
        "Dashboard.html",
        {
            "request": request,
            "role": role,
            "transactions": transactions,
            "summary": calculate_summary(transactions),
            "category_breakdown": category_data,
            "monthly_summary": monthly_data
        }
    )


# ================= FORM CREATE (FIX) =================
@router.post("/transactions/create")
def create_transaction_form(
    request: Request,
    amount: float = Form(...),
    type: str = Form(...),
    category: str = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    role = get_role(request)

    if role != "admin":
        raise HTTPException(status_code=403)

    txn = Transaction(
        amount=amount,
        type=type,
        category=category,
        date=datetime.strptime(date, "%Y-%m-%d").date(),
        notes=notes
    )

    db.add(txn)
    db.commit()

    return RedirectResponse("/dashboard", status_code=303)


# ================= FORM DELETE (FIX) =================
@router.post("/transactions/delete/{transaction_id}")
def delete_transaction_form(
    transaction_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    role = get_role(request)

    if role != "admin":
        raise HTTPException(status_code=403)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if txn:
        db.delete(txn)
        db.commit()

    return RedirectResponse("/dashboard", status_code=303)


# ================= EXISTING API (UNCHANGED) =================

@router.get("/api/transactions")
def get_transactions(
    request: Request,
    db: Session = Depends(get_db),
    type: str = Query(None),
    category: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=100)
):
    get_role(request)

    query = db.query(Transaction)

    if type:
        query = query.filter(Transaction.type == type)

    if category:
        query = query.filter(Transaction.category.ilike(f"%{category}%"))

    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, "%Y-%m-%d").date())

    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    if search:
        query = query.filter(
            or_(
                Transaction.category.ilike(f"%{search}%"),
                Transaction.notes.ilike(f"%{search}%")
            )
        )

    total = query.count()
    data = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "data": data
    }


@router.post("/api/transactions")
def create_transaction_api(request: Request, payload: TransactionCreate, db: Session = Depends(get_db)):
    role = get_role(request)

    if role != "admin":
        raise HTTPException(status_code=403)

    txn = Transaction(**payload.dict())
    db.add(txn)
    db.commit()

    return {"message": "Transaction created"}


@router.delete("/api/transactions/{transaction_id}")
def delete_transaction_api(transaction_id: int, request: Request, db: Session = Depends(get_db)):
    role = get_role(request)

    if role != "admin":
        raise HTTPException(status_code=403)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not txn:
        raise HTTPException(status_code=404)

    db.delete(txn)
    db.commit()

    return {"message": "Deleted successfully"}


# ================= CSV =================
# ================= CSV EXPORT (FINAL WORKING) =================
@router.get("/api/transactions/export")
def export_csv(request: Request, db: Session = Depends(get_db)):
    get_role(request)

    transactions = db.query(Transaction).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["ID", "Amount", "Type", "Category", "Date", "Notes"])

    for t in transactions:
        writer.writerow([t.id, t.amount, t.type, t.category, t.date, t.notes])

    csv_data = output.getvalue()
    output.close()

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=project-by-jay-finance-data.csv"
        }
    )

@router.post("/api/transactions/import")
def import_csv(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    role = get_role(request)

    if role != "admin":
        raise HTTPException(status_code=403)

    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        try:
            txn = Transaction(
                amount=float(row["Amount"]),
                type=row["Type"],
                category=row["Category"],
                date=datetime.strptime(row["Date"], "%Y-%m-%d").date(),
                notes=row.get("Notes", "")
            )
            db.add(txn)
        except:
            continue

    db.commit()

    return RedirectResponse("/dashboard", status_code=303)

# ================= FORM DELETE (UI SUPPORT) =================
@router.post("/transactions/delete/{transaction_id}")
def delete_transaction_form(
    transaction_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    role = get_role(request)

    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


# ================= FORM EDIT (WORKING WITH DASHBOARD) =================
@router.post("/transactions/edit/{transaction_id}")
def edit_transaction_form(
    transaction_id: int,
    request: Request,
    amount: float = Form(...),
    type: str = Form(...),
    category: str = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    role = get_role(request)

    if role != "admin":
        raise HTTPException(status_code=403)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not txn:
        raise HTTPException(status_code=404)

    # ✅ update values
    txn.amount = amount
    txn.type = type
    txn.category = category
    txn.date = datetime.strptime(date, "%Y-%m-%d").date()
    txn.notes = notes

    db.commit()

    return RedirectResponse("/dashboard", status_code=303)

