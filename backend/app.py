from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from studio.router import router as studio_router
from studio.chat import router as chat_router

from config.logging import setup_logging
from config.settings import settings
from exceptions.handlers import register_global_handlers, request_id_ctx_var
from database.session import AsyncSessionLocal
from database.models.food import Food
from database.models.cuisine import Cuisine
from sqlalchemy import select

import asyncio
import uuid
from fastapi import Request
from repositories.meal_repository import set_main_loop

setup_logging()

app = FastAPI(title="Diet Plan Studio API")
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
    FastAPI startup lifecycle event. Sets up the main asyncio event loop reference
    for background tasks and pre-compiles/loads the substitute index cache from PostgreSQL.
    """
    loop = asyncio.get_running_loop()
    set_main_loop(loop)
    
    # Initialize substitute repository cache
    try:
        from repositories.substitute_repository import substitute_repository
        await substitute_repository.initialize_cache()
    except Exception as e:
        import sys
        print(f"CRITICAL: Failed to initialize substitute repository cache: {e}", file=sys.stderr)
        sys.exit(1)

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

@app.get("/api/health")
def health():
    """
    Liveness and health status check endpoint.
    """
    return {"ok": True}

@app.get("/api/food-image/{food_id}")
async def get_food_image(food_id: str):
    """
    Fetches the local image file path from the database metadata and streams it 
    to the client. Returns 404 if not found or if the file is missing on disk.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(Food.image_url).filter(Food.id == food_id)
        res = await session.execute(stmt)
        image_url = res.scalar()
        if not image_url:
            return JSONResponse(status_code=404, content={"detail": "Image not found for food_id"})
        
    images_root = settings.image_root
    file_path = os.path.join(images_root, image_url)
    
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"detail": "Image file missing"})
        
    return FileResponse(file_path)


app.include_router(studio_router)
app.include_router(chat_router)

