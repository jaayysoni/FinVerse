from sqlalchemy import Column, Integer, Float, String, Date, DateTime, CheckConstraint, Index # type: ignore
from datetime import datetime
from app.db.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    category = Column(String, nullable=False)

    date = Column(Date, nullable=False)
    notes = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_amount_positive"),
        CheckConstraint("type IN ('income', 'expense')", name="check_type_valid"),
        Index("idx_type", "type"),
        Index("idx_category", "category"),
        Index("idx_date", "date"),
    )