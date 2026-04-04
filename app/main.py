# app/main.py
from fastapi import FastAPI
from app.api.routes import users  # import only users.py for now

app = FastAPI(title="FinVerse App")

# Include the user router which has login and dashboard routes
app.include_router(users.router)