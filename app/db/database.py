from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ✅ This is the missing part: get_db dependency
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()