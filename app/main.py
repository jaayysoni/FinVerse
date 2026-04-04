from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.db.database import engine
from app.db import base  # registers all models
from app.db.base import Base
from app.api.routes import transactions, users, summary, views

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Python-based Finance Tracking System — FinVerse",
)

# API routes
app.include_router(transactions.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(summary.router, prefix="/api")

# HTML view routes
app.include_router(views.router)