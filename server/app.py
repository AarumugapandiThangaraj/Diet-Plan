from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from studio.router import router as studio_router
# from studio.chat import router as chat_router
# from admin.router import router as admin_router

from config.logging import setup_logging
from config.settings import settings
from exceptions.handlers import register_global_handlers, request_id_ctx_var
from database.session import AsyncSessionLocal
from sqlalchemy import select

import asyncio
import uuid
from fastapi import Request
from repositories.meal_repository import set_main_loop
from schemas import HealthResponse, ErrorResponse

setup_logging()

app = FastAPI(
    title="Diet Plan Studio API",
    description="AI-powered nutrition planning, meal recommendation, and dietary swap platform designed for customized wellness solutions.",
    version="1.0.0",
    contact={
        "name": "Diet Plan Studio Support",
        "email": "support@dietplanstudio.com",
    },
    openapi_tags=[
        {
            "name": "System",
            "description": "General system health, uptime check, and system configuration information."
        },
        {
            "name": "Planner",
            "description": "Calculate daily calorie/macro targets and generate structured multi-day nutrition plans based on individual profiles."
        },
        {
            "name": "Nutrition",
            "description": "Rank, retrieve, and score meal/recipe candidates against customized calorie and macronutrient requirements."
        },
        {
            "name": "Swaps",
            "description": "Suggest and apply alternative options for whole meals, individual foods, or specific ingredients."
        },
        {
            "name": "Substitutions",
            "description": "Query specific ingredient substitutes based on database mappings and nutrient scaling ratios."
        },
        {
            "name": "Chat",
            "description": "Engage with an AI nutrition assistant for real-time preferences adjustments, recommendations, or conversational meal planning."
        },
        {
            "name": "Images",
            "description": "Serve recipe and food images resolved dynamically from database records."
        }
    ]
)
register_global_handlers(app)

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """
    HTTP middleware to add a unique request/correlation ID to the request context 
    and output headers for distributed request tracing.
    """
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_ctx_var.set(req_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
    finally:
        request_id_ctx_var.reset(token)

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup lifecycle event. Captures the main asyncio event loop reference
    so that sync threadpool endpoints can schedule async DB coroutines on the correct
    loop via asyncio.run_coroutine_threadsafe, preventing the
    'Future attached to a different loop' RuntimeError.
    """
    loop = asyncio.get_running_loop()
    set_main_loop(loop)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


import json
import os
from fastapi.responses import FileResponse, JSONResponse

@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check API Health Status",
    description="Provides a liveness check to verify if the server is healthy, up, and responsive.",
    responses={
        200: {
            "description": "API server is healthy and operational.",
            "model": HealthResponse
        },
        500: {
            "description": "Internal server error indicating the system is unhealthy.",
            "model": ErrorResponse
        }
    }
)
def health():
    """
    Liveness and health status check endpoint.
    """
    return {"ok": True}

# @app.get(
#     "/api/meal-image/{meal_id}",
#     tags=["Images","dev"],
#     summary="Get Food Image File",
#     description=(
#         "Retrieves the local image file associated with a food/recipe ID. "
#         "Looks up the metadata details from the PostgreSQL database, resolves the relative file path "
#         "from the system configuration settings, and streams the raw image bytes back to the client. "
#         "Returns a 404 response if either the image record database lookup fails or the physical image file is missing on disk."
#     ),
#     responses={
#         200: {
#             "description": "Streaming image file response (e.g. image/jpeg, image/png).",
#             "content": {
#                 "image/*": {}
#             }
#         },
#         404: {
#             "description": "Image database entry not found or physical file missing on disk.",
#             "content": {
#                 "application/json": {
#                     "example": {"detail": "Image not found for meal_id"}
#                 }
#             }
#         },
#         500: {
#             "description": "Internal database or filesystem failure.",
#             "model": ErrorResponse
#         }
#     }
# )
# async def get_food_image(meal_id: str):
#     """
#     Fetches the local image file path from the database metadata and streams it 
#     to the client. Returns 404 if not found or if the file is missing on disk.
#     """
#     # from database.models import Meal
    
#     # image_url = None
#     # async with AsyncSessionLocal() as session:
#     #     # Check if the meal_id represents a direct filename with an image extension
#     #     if any(meal_id.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
#     #         stmt = select(Meal.image).filter(Meal.image.like(f"%{meal_id}"))
#     #         res = await session.execute(stmt)
#     #         image_url = res.scalar()

#     #         # Fallback to the raw meal_id if still not found in database
#     #         if not image_url:
#     #             image_url = meal_id
#     #     else:
#     #         stmt = select(Meal.image).filter(Meal.id == meal_id)
#     #         res = await session.execute(stmt)
#     #         image_url = res.scalar()

#     #     if not image_url:
#     #         return JSONResponse(status_code=404, content={"detail": "Image not found for meal_id"})
        
#     # images_root = settings.image_root
#     # file_path = os.path.join(images_root, image_url)
#     import os
#     # Create an absolute path relative to the location of app.py
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     temp_file_path = os.path.join(base_dir, "assets", "images", "continental", "tuscan_grilled_chicken_2.webp")
    
#     if not os.path.exists(temp_file_path):
#         return JSONResponse(status_code=404, content={"detail": "Hardcoded test image file missing"})
        
#     return FileResponse(temp_file_path, media_type="image/webp")


app.include_router(studio_router)
# app.include_router(chat_router)
# app.include_router(admin_router)

