# app/crud/transaction.py
from sqlalchemy.orm import Session
from app.db.models import Transaction

# ==================== GET ====================

def get_all_transactions(db: Session):
    """Return all transactions"""
    return db.query(Transaction).all()


def get_transactions_query(db: Session):
    """Return a query object (can be filtered later)"""
    return db.query(Transaction)


def get_transactions(db: Session, type: str = None, category: str = None,
                     start_date: str = None, end_date: str = None):
    """
    Fetch transactions with optional filters
    """
    query = get_transactions_query(db)
    
    if type:
        query = query.filter(Transaction.type == type)
    
    if category:
        query = query.filter(Transaction.category.ilike(f"%{category}%"))
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    
    return query.order_by(Transaction.date.desc()).all()


# ==================== CREATE ====================

def create_transaction(db: Session, amount: float, type: str, category: str,
                       date: str, notes: str):
    t = Transaction(
        amount=amount,
        type=type,
        category=category,
        date=date,
        notes=notes
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# ==================== UPDATE ====================

def update_transaction(db: Session, transaction_id: int, amount: float,
                       type: str, category: str, date: str, notes: str):
    t = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if t:
        t.amount = amount
        t.type = type
        t.category = category
        t.date = date
        t.notes = notes
        db.commit()
        db.refresh(t)
    return t


# ==================== DELETE ====================

def delete_transaction(db: Session, transaction_id: int):
    t = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if t:
        db.delete(t)
        db.commit()
    return t