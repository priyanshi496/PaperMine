from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
from app.db.database import get_db
from app.services.assistant import run_assistant_query
from app.db import models
from app.api.deps import get_current_user

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    chat_history: List[Dict[str, str]] = []

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Handles queries to the Hybrid Assistant.
    Runs blocking FAISS + Ollama calls in a thread pool to avoid
    blocking the FastAPI async event loop.
    Injects the user's vendor_id if they are a vendor, scoping all data.
    """
    vendor_id = current_user.vendor_id if current_user.role == "vendor" else None
    
    result = await asyncio.to_thread(
        run_assistant_query, db, request.query, request.chat_history, vendor_id
    )
    return result
