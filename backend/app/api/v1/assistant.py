from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
from app.db.database import get_db
from app.services.assistant import run_assistant_query

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    chat_history: List[Dict[str, str]] = []

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Handles queries to the Hybrid Assistant.
    Runs blocking FAISS + Ollama calls in a thread pool to avoid
    blocking the FastAPI async event loop (fixes MacOS PyTorch deadlock).
    """
    result = await asyncio.to_thread(
        run_assistant_query, db, request.query, request.chat_history
    )
    return result
