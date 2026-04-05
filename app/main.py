from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from app.api.routes import users

app = FastAPI()

# 🔥 THIS IS THE FIX
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

app.include_router(users.router)