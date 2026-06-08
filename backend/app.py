from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from studio.router import router as studio_router
from studio.chat import router as chat_router

from config.logging import setup_logging
from config.errors import register_error_handlers
from database.session import AsyncSessionLocal
from database.models.food import Food
from database.models.cuisine import Cuisine
from sqlalchemy import select

import asyncio
from repositories.meal_repository import set_main_loop

setup_logging()

app = FastAPI(title="Diet Plan Studio API")
register_error_handlers(app)

@app.on_event("startup")
async def startup_event():
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

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/food-image/{food_id}")
async def get_food_image(food_id: str):
    async with AsyncSessionLocal() as session:
        stmt = select(Food.image_url).filter(Food.id == food_id)
        res = await session.execute(stmt)
        image_url = res.scalar()
        if not image_url:
            return JSONResponse(status_code=404, content={"detail": "Image not found for food_id"})
        
    images_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data new", "Images"))
    file_path = os.path.join(images_root, image_url)
    
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"detail": "Image file missing"})
        
    return FileResponse(file_path)


app.include_router(studio_router)
app.include_router(chat_router)

