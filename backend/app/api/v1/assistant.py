from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
from app.db.database import get_db
from app.services.assistant import run_assistant_query, run_assistant_query_stream
from app.db import models
from app.api.deps import get_current_user

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, str]]] = None
    frontend_context: Optional[Dict[str, Any]] = None

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Handles queries to the Hybrid Assistant.
    Returns a stream of data.
    Injects the user's vendor_id if they are a vendor, scoping all data.
    Also passes user_role so the LLM can adopt the correct persona.
    """
    vendor_id = current_user.vendor_id if current_user.role == "vendor" else None
    user_role = current_user.role  # "vendor" | "finance_team" | "cfo" | "admin"
    user_email = current_user.email

    return StreamingResponse(
        run_assistant_query_stream(
            db,
            request.query,
            request.chat_history,
            vendor_id,
            request.frontend_context,
            user_role=user_role,
            user_email=user_email,
        ),
        media_type="text/event-stream"
    )
