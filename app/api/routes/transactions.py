from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from app.api.deps import get_db
from app.crud import transaction as crud_transaction

router = APIRouter()
templates = Jinja2Templates(directory="app/Templates")