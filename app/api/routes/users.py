from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
import csv
import io

from app.db.database import get_db
from app.models.transaction import Transaction

router = APIRouter()
templates = Jinja2Templates(directory="app/Templates")

# CONSTANTS

VALID_ROLES = ["admin", "analyst", "viewer"]
VALID_TYPES = ["income", "expense"]


# SCHEMAS (Pydantic)

class TransactionCreate(BaseModel):
    amount: float = Field(gt=0, description="Must be a positive number")
    type: str = Field(description="Either 'income' or 'expense'")
    category: str
    date: date
    notes: str = ""

    @validator("type")
    def validate_type(cls, v):
        if v not in VALID_TYPES:
            raise ValueError(f"Type must be one of: {VALID_TYPES}")
        return v


class TransactionUpdate(BaseModel):
    amount: float = Field(gt=0)
    type: str
    category: str
    date: date
    notes: str = ""

    @validator("type")
    def validate_type(cls, v):
        if v not in VALID_TYPES:
            raise ValueError(f"Type must be one of: {VALID_TYPES}")
        return v


# RBAC HELPERS

def get_role(request: Request) -> str:
    """
    Reads role from session. Raises 401 if not logged in, 403 if role is invalid.
    """
    role = request.session.get("role")
    if not role:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=403, detail="Invalid role")
    return role


def require_admin(request: Request) -> str:
    """
    Shortcut: raises 403 if the session role is not 'admin'.
    """
    role = get_role(request)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return role


# ANALYTICS HELPERS

def calculate_summary(transactions: list) -> dict:
    """
    Returns total income, total expense, and balance from a list of transactions.
    """
    income  = sum(t.amount for t in transactions if t.type == "income")
    expense = sum(t.amount for t in transactions if t.type == "expense")
    return {
        "total_income":  income,
        "total_expense": expense,
        "balance":       income - expense,
    }


def apply_filters(query, type, category, start_date, end_date, search):
    """
    Applies optional filters to a SQLAlchemy query and returns the modified query.
    All parameters are optional (pass None to skip).
    """
    if type:
        query = query.filter(Transaction.type == type)

    if category:
        query = query.filter(Transaction.category.ilike(f"%{category}%"))

    if start_date:
        query = query.filter(
            Transaction.date >= datetime.strptime(start_date, "%Y-%m-%d").date()
        )

    if end_date:
        query = query.filter(
            Transaction.date <= datetime.strptime(end_date, "%Y-%m-%d").date()
        )

    if search:
        query = query.filter(
            or_(
                Transaction.category.ilike(f"%{search}%"),
                Transaction.notes.ilike(f"%{search}%"),
            )
        )

    return query


def apply_sorting(query, sort: str):
    """
    Applies sorting to a SQLAlchemy query.
    Supported values: date_desc, date_asc, amount_desc, amount_asc.
    Defaults to date_desc.
    """
    sort_map = {
        "date_desc":   Transaction.date.desc(),
        "date_asc":    Transaction.date.asc(),
        "amount_desc": Transaction.amount.desc(),
        "amount_asc":  Transaction.amount.asc(),
    }
    order = sort_map.get(sort, Transaction.date.desc())
    return query.order_by(order)


# AUTH ROUTES

@router.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(request: Request, role: str = Form(...)):
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {VALID_ROLES}")
    request.session["role"] = role
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


# DASHBOARD ROUTE

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    edit_id: int = Query(None),
    type: str = Query(None),
    category: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    search: str = Query(None),
    sort: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    role = get_role(request)

    # Base query
    query = db.query(Transaction)
    query = apply_filters(query, type, category, start_date, end_date, search)
    query = apply_sorting(query, sort)

    total = query.count()
    transactions = query.offset((page - 1) * limit).limit(limit).all()

    category_data = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label("total"),
    ).group_by(Transaction.category).all()

    monthly_data = db.query(
        func.strftime("%Y-%m", Transaction.date).label("month"),
        func.sum(Transaction.amount).label("total"),
    ).group_by("month").all()

    all_transactions = db.query(Transaction).all()

    txn_to_edit = None
    if edit_id:
        txn_to_edit = db.query(Transaction).filter(Transaction.id == edit_id).first()

    return templates.TemplateResponse(
        "Dashboard.html",
        {
            "request": request,
            "role": role,
            "transactions": transactions,
            "summary": calculate_summary(all_transactions),
            "category_breakdown": category_data,
            "monthly_summary": monthly_data,
            "total": total,
            "page": page,
            "limit": limit,
            "edit_transaction": txn_to_edit,
        },
    )

# UI FORM ROUTES

@router.post("/transactions/create")
def form_create_transaction(
    request:  Request,
    amount:   float = Form(...),
    type:     str   = Form(...),
    category: str   = Form(...),
    date:     str   = Form(...),
    notes:    str   = Form(""),
    db:       Session = Depends(get_db),
):
    require_admin(request)

    if type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Type must be one of: {VALID_TYPES}")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    txn = Transaction(
        amount   = amount,
        type     = type,
        category = category,
        date     = datetime.strptime(date, "%Y-%m-%d").date(),
        notes    = notes,
    )
    db.add(txn)
    db.commit()

    return RedirectResponse("/dashboard", status_code=303)

#  DASHBOARD FORM EDIT 
@router.post("/transactions/edit/{transaction_id}")
def form_edit_transaction(
    transaction_id: int,
    request: Request,
    amount: float = Form(...),
    type: str = Form(...),
    category: str = Form(...),
    date: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Edit a transaction via the dashboard form.
    Admin only.
    """
    require_admin(request)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Type must be one of: {VALID_TYPES}")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    txn.amount = amount
    txn.type = type
    txn.category = category
    txn.date = datetime.strptime(date, "%Y-%m-%d").date()
    txn.notes = notes
    db.commit()

# Redirect back to dashboard after editing
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, edit_id: int = None, db: Session = Depends(get_db)):
    require_admin(request)

    all_transactions = db.query(Transaction).all()
    summary = calculate_summary(all_transactions)

    txn_to_edit = None
    if edit_id:
        txn_to_edit = db.query(Transaction).filter(Transaction.id == edit_id).first()

    return templates.TemplateResponse("Dashboard.html", {
        "request": request,
        "transactions": all_transactions,
        "summary": summary,
        "edit_transaction": txn_to_edit,  # this will be None if not editing
    })


# REST API EDIT 
@router.put("/api/transactions/{transaction_id}", summary="Update an existing transaction")
def update_transaction(
    transaction_id: int,
    request: Request,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
):
    """
    Fully updates a transaction. Admin only.
    """
    require_admin(request)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.amount = payload.amount
    txn.type = payload.type
    txn.category = payload.category
    txn.date = payload.date
    txn.notes = payload.notes

    db.commit()
    db.refresh(txn)

    return {"message": "Transaction updated", "id": txn.id}

# DELETE TRANSACTION 
@router.post("/transactions/delete/{transaction_id}")
def form_delete_transaction(
    transaction_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()

    # Redirect back to dashboard after deletion
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/transactions/delete/{transaction_id}")
def form_delete_transaction(
    transaction_id: int,
    request:        Request,
    db:             Session = Depends(get_db),
):
    require_admin(request)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()

    return RedirectResponse("/dashboard", status_code=303)



@router.post("/transactions/import")
def form_import_csv(
    request: Request,
    file:    UploadFile = File(...),
    db:      Session = Depends(get_db),
):
    require_admin(request)

    content  = file.file.read().decode("utf-8")
    reader   = csv.DictReader(io.StringIO(content))
    imported = 0
    skipped  = 0

    for row in reader:
        try:
            amount = float(row["Amount"])
            type_  = row["Type"].strip().lower()

            if type_ not in VALID_TYPES or amount <= 0:
                skipped += 1
                continue

            txn = Transaction(
                amount   = amount,
                type     = type_,
                category = row["Category"].strip(),
                date     = datetime.strptime(row["Date"].strip(), "%Y-%m-%d").date(),
                notes    = row.get("Notes", "").strip(),
            )
            db.add(txn)
            imported += 1
        except Exception:
            skipped += 1
            continue

    db.commit()

    return RedirectResponse("/dashboard", status_code=303)



@router.get("/api/transactions", summary="List transactions with filters and pagination")
def list_transactions(
    request:    Request,
    db:         Session = Depends(get_db),
    type:       str = Query(None, description="Filter by 'income' or 'expense'"),
    category:   str = Query(None, description="Partial match on category"),
    start_date: str = Query(None, description="Format: YYYY-MM-DD"),
    end_date:   str = Query(None, description="Format: YYYY-MM-DD"),
    search:     str = Query(None, description="Search in category and notes"),
    sort:       str = Query(None, description="date_desc | date_asc | amount_desc | amount_asc"),
    page:       int = Query(1,  ge=1),
    limit:      int = Query(10, le=100),
):

    get_role(request)

    query = db.query(Transaction)
    query = apply_filters(query, type, category, start_date, end_date, search)
    query = apply_sorting(query, sort)

    total = query.count()
    data  = query.offset((page - 1) * limit).limit(limit).all()

    return {"total": total, "page": page, "limit": limit, "data": data}




@router.get("/api/transactions/export", summary="Export all transactions as CSV")
def export_csv(
    request: Request,
    db:      Session = Depends(get_db),
):

    get_role(request)

    transactions = db.query(Transaction).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Amount", "Type", "Category", "Date", "Notes"])
    for t in transactions:
        writer.writerow([t.id, t.amount, t.type, t.category, t.date, t.notes])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance-data.csv"},
    )


@router.post("/api/transactions/import", summary="Import transactions from a CSV file (REST API)")
def import_csv(
    request: Request,
    file:    UploadFile = File(...),
    db:      Session = Depends(get_db),
):
    """
    Bulk-imports transactions from a CSV file.
    Expected columns: Amount, Type, Category, Date, Notes.
    Admin only. Returns JSON.
    Use POST /transactions/import for the dashboard form instead.
    """
    require_admin(request)

    content  = file.file.read().decode("utf-8")
    reader   = csv.DictReader(io.StringIO(content))
    imported = 0
    skipped  = 0

    for row in reader:
        try:
            txn = Transaction(
                amount   = float(row["Amount"]),
                type     = row["Type"].strip().lower(),
                category = row["Category"].strip(),
                date     = datetime.strptime(row["Date"].strip(), "%Y-%m-%d").date(),
                notes    = row.get("Notes", "").strip(),
            )
            db.add(txn)
            imported += 1
        except Exception:
            skipped += 1
            continue

    db.commit()

    return {"message": "Import complete", "imported": imported, "skipped": skipped}



@router.get("/api/transactions/{transaction_id}", summary="Get a single transaction by ID")
def get_transaction(
    transaction_id: int,
    request:        Request,
    db:             Session = Depends(get_db),
):

    get_role(request)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return txn


@router.post("/api/transactions", status_code=201, summary="Create a new transaction")
def create_transaction(
    request: Request,
    payload: TransactionCreate,
    db:      Session = Depends(get_db),
):

    require_admin(request)

    txn = Transaction(**payload.dict())
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return {"message": "Transaction created", "id": txn.id}


@router.put("/api/transactions/{transaction_id}", summary="Update an existing transaction")
def update_transaction(
    transaction_id: int,
    request:        Request,
    payload:        TransactionUpdate,
    db:             Session = Depends(get_db),
):

    require_admin(request)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.amount   = payload.amount
    txn.type     = payload.type
    txn.category = payload.category
    txn.date     = payload.date
    txn.notes    = payload.notes

    db.commit()
    db.refresh(txn)

    return {"message": "Transaction updated", "id": txn.id}


@router.delete("/api/transactions/{transaction_id}", summary="Delete a transaction")
def delete_transaction(
    transaction_id: int,
    request:        Request,
    db:             Session = Depends(get_db),
):

    require_admin(request)

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()

    return {"message": "Transaction deleted", "id": transaction_id}


# REST API — ANALYTICS / SUMMARY

@router.get("/api/summary", summary="Get financial summary (income, expense, balance)")
def get_summary(
    request: Request,
    db:      Session = Depends(get_db),
):

    get_role(request)
    return calculate_summary(db.query(Transaction).all())


@router.get("/api/summary/category", summary="Category-wise breakdown of totals")
def get_category_breakdown(
    request: Request,
    db:      Session = Depends(get_db),
):

    role = get_role(request)
    if role not in ["analyst", "admin"]:
        raise HTTPException(status_code=403, detail="Analyst or Admin access required")

    data = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label("total"),
    ).group_by(Transaction.category).all()

    return [{"category": row.category, "total": row.total} for row in data]


@router.get("/api/summary/monthly", summary="Monthly totals")
def get_monthly_summary(
    request: Request,
    db:      Session = Depends(get_db),
):

    role = get_role(request)
    if role not in ["analyst", "admin"]:
        raise HTTPException(status_code=403, detail="Analyst or Admin access required")

    data = db.query(
        func.strftime("%Y-%m", Transaction.date).label("month"),
        func.sum(Transaction.amount).label("total"),
    ).group_by("month").all()

    return [{"month": row.month, "total": row.total} for row in data]


@router.get("/api/summary/recent", summary="10 most recent transactions")
def get_recent_transactions(
    request: Request,
    db:      Session = Depends(get_db),
):

    get_role(request)
    return db.query(Transaction).order_by(Transaction.date.desc()).limit(10).all()

