from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
from app.db.database import get_db
from app.services.assistant import run_assistant_query

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    chat_history: List[Dict[str, str]] = [] # e.g. [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    
@router.post("/chat")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Handles queries to the Hybrid Assistant.
    """
    result = run_assistant_query(db, request.query, request.chat_history)
    return result
