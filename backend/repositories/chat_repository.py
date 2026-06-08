"""
Chat Repository

Data access layer managing default user choices, preferences (likes, dislikes, allergies, notes),
and medical profiles in PostgreSQL.
"""

import asyncio
import concurrent.futures
from sqlalchemy import select
from database.session import AsyncSessionLocal
from database.models.preference import UserPreference

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        return loop.run_until_complete(coro)

async def _load_preferences_async() -> dict:
    async with AsyncSessionLocal() as session:
        stmt = select(UserPreference).filter_by(user_identifier="default_user")
        res = await session.execute(stmt)
        pref_obj = res.scalar_one_or_none()
        if pref_obj:
            return {
                "likes": pref_obj.likes or [],
                "dislikes": pref_obj.dislikes or [],
                "allergies": pref_obj.allergies or [],
                "notes": pref_obj.notes or []
            }
        return {"likes": [], "dislikes": [], "allergies": [], "notes": []}

async def _save_preferences_async(prefs: dict) -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(UserPreference).filter_by(user_identifier="default_user")
        res = await session.execute(stmt)
        pref_obj = res.scalar_one_or_none()
        if not pref_obj:
            pref_obj = UserPreference(
                user_identifier="default_user",
                likes=prefs.get("likes") or [],
                dislikes=prefs.get("dislikes") or [],
                allergies=prefs.get("allergies") or [],
                notes=prefs.get("notes") or []
            )
            session.add(pref_obj)
        else:
            pref_obj.likes = prefs.get("likes") or []
            pref_obj.dislikes = prefs.get("dislikes") or []
            pref_obj.allergies = prefs.get("allergies") or []
            pref_obj.notes = prefs.get("notes") or []
        await session.commit()

def load_preferences() -> dict:
    try:
        return run_async(_load_preferences_async())
    except Exception:
        return {"likes": [], "dislikes": [], "allergies": [], "notes": []}

def save_preferences(prefs: dict) -> None:
    try:
        run_async(_save_preferences_async(prefs))
    except Exception as e:
        print(f"Error saving preferences: {e}")
