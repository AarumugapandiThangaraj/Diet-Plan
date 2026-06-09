from __future__ import annotations

import logging
import traceback
from fastapi import APIRouter, HTTPException

from schemas import ChatRequest, ChatResponse
from ai.ai_agent import process_chat_message

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger("app.chat")

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    result = process_chat_message(
        message=req.message,
        history=req.history,
        agent_name=req.agentName,
        context=req.context or {}
    )
    return ChatResponse(
        reply=result.get("reply", ""),
        preferences=result.get("preferences"),
        quickReplies=result.get("quickReplies"),
        action=result.get("action")
    )

