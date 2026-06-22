from datetime import date, datetime
from typing import Optional
from sqlalchemy import select, func, cast, Date
from database.session import AsyncSessionLocal
from database.models import UserHydrationLog
from sqlalchemy.exc import SQLAlchemyError
from exceptions.repository import RepositoryException
import uuid

class MockUserWaterLog:
    def __init__(self, user_identifier: str, log_date: date, water_ml: int):
        self.user_identifier = user_identifier
        self.log_date = log_date
        self.water_ml = water_ml

async def get_water_consumption_log(user_identifier: str, log_date: date) -> Optional[MockUserWaterLog]:
    """
    Asynchronously retrieves the water consumption log for a user on a specific date.
    Aggregates volume_ml from UserHydrationLog for the day.
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
            except ValueError:
                return None
                
            stmt = select(func.sum(UserHydrationLog.volume_ml)).filter(
                UserHydrationLog.user_id == uid,
                cast(UserHydrationLog.logged_at, Date) == log_date
            )
            res = await session.execute(stmt)
            total_ml = res.scalar() or 0
            
            if total_ml > 0:
                return MockUserWaterLog(user_identifier, log_date, int(total_ml))
            return None
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to load user water log from repository") from ex

async def save_water_consumption_log(
    user_identifier: str,
    log_date: date,
    water_ml: int
) -> MockUserWaterLog:
    """
    Asynchronously appends to user daily water consumption log to match the target water_ml.
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
            except ValueError:
                raise RepositoryException("Invalid user identifier format (expected UUID)")
                
            # Get current sum
            stmt = select(func.sum(UserHydrationLog.volume_ml)).filter(
                UserHydrationLog.user_id == uid,
                cast(UserHydrationLog.logged_at, Date) == log_date
            )
            res = await session.execute(stmt)
            current_ml = res.scalar() or 0
            
            delta = water_ml - current_ml
            if delta != 0:
                # Approximate glasses (e.g., 250ml per glass)
                glasses = max(1, abs(delta) // 250)
                
                log_obj = UserHydrationLog(
                    user_id=uid,
                    glasses=glasses,
                    volume_ml=delta,
                    source='manual'
                )
                session.add(log_obj)
                await session.commit()
                
            return MockUserWaterLog(user_identifier, log_date, water_ml)
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to save user water log to repository") from ex
