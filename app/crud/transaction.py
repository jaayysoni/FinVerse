from sqlalchemy.orm import Session
from app.models.transaction import Transaction

def get_all_transactions(db: Session):
    return db.query(Transaction).all()