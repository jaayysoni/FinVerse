# app/crud/transaction.py
from sqlalchemy.orm import Session
from app.db.models import Transaction

def get_all_transactions(db: Session):
    return db.query(Transaction).all()

def get_transactions_query(db: Session):
    return db.query(Transaction)