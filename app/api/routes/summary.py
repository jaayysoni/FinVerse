from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.api.deps import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/Templates")