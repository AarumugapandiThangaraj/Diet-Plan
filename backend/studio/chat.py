from __future__ import annotations

import logging
import traceback
from fastapi import APIRouter, HTTPException

from schemas import ChatRequest, ChatResponse, ErrorResponse
from ai.ai_agent import process_chat_message

router = APIRouter(prefix="/api", tags=["Chat"])
logger = logging.getLogger("app.chat")

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send Chat Message to AI Nutritionist",
    description=(
        "Sends a conversational query to the AI nutrition companion (NutriBot) to interactively "
        "adjust plan preferences, get recipe recommendations, perform swaps, or ask nutrition questions.\n\n"
        "### Key Features:\n"
        "- **Conversational Context/Memory**: Pass prior messages in the `history` array to preserve conversation context. "
        "The agent parses this history to build a persistent context map.\n"
        "- **Structured Actions**: The AI companion can return recommended actions (like swapping a meal) in the response payload "
        "which can be parsed by the frontend to trigger UI updates.\n"
        "- **Context Injection**: Pass additional frontend state (like current selected meal time or target calories) "
        "in the `context` field to tailor recommendations.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/chat \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"message\": \"Can you swap my high protein breakfast for something lighter?\",\n"
        "    \"history\": [\n"
        "      {\"role\": \"user\", \"text\": \"Hi, I am planning my meals.\"},\n"
        "      {\"role\": \"assistant\", \"text\": \"Hello! I can help you plan your diet.\"}\n"
        "    ],\n"
        "    \"agentName\": \"NutriBot\",\n"
        "    \"context\": {\n"
        "      \"current_meal_time\": \"breakfast\",\n"
        "      \"calories_target\": 450\n"
        "    }\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Successfully processed the chat query and returned the agent response.",
            "model": ChatResponse
        },
        400: {
            "description": "Invalid input formatting or request payload structure.",
            "model": ErrorResponse
        },
        500: {
            "description": "Failed to process chat query via AI companion service due to connection or configuration issues.",
            "model": ErrorResponse
        }
    }
)
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

