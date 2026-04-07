# app/main.py
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from app.api.routes import users
from pathlib import Path

app = FastAPI()

# Session middleware
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# Include routes
app.include_router(users.router)
