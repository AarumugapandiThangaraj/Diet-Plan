from datetime import date, datetime
from typing import Optional
from sqlalchemy import select, func, cast, Date
from database.session import AsyncSessionLocal
from database.models import DietPlanDayHydrationLog
from sqlalchemy.exc import SQLAlchemyError
from exceptions.repository import RepositoryException
import uuid

class MockUserWaterLog:
    def __init__(self, user_identifier: str, plan_day_id: str, water_ml: int):
        self.user_identifier = user_identifier
        self.plan_day_id = plan_day_id
        self.water_ml = water_ml

async def get_water_consumption_log(user_identifier: str, plan_day_id: str) -> Optional[MockUserWaterLog]:
    """
    Asynchronously retrieves the water consumption log for a specific diet plan day.
    Aggregates volume_ml from DietPlanDayHydrationLog for the day.
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
                pdid = uuid.UUID(plan_day_id)
            except ValueError:
                return None
                
            stmt = select(func.sum(DietPlanDayHydrationLog.volume_ml)).filter(
                DietPlanDayHydrationLog.user_id == uid,
                DietPlanDayHydrationLog.plan_day_id == pdid
            )
            res = await session.execute(stmt)
            total_ml = res.scalar() or 0
            
            if total_ml > 0:
                return MockUserWaterLog(user_identifier, plan_day_id, int(total_ml))
            return None
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to load user water log from repository") from ex

async def save_water_consumption_log(
    user_identifier: str,
    plan_day_id: str,
    water_ml: int
) -> MockUserWaterLog:
    """
    Asynchronously appends to user daily water consumption log to match the target water_ml.
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
                pdid = uuid.UUID(plan_day_id)
            except ValueError:
                raise RepositoryException("Invalid user identifier or plan day format (expected UUID)")
                
            # Get current sum
            stmt = select(func.sum(DietPlanDayHydrationLog.volume_ml)).filter(
                DietPlanDayHydrationLog.user_id == uid,
                DietPlanDayHydrationLog.plan_day_id == pdid
            )
            res = await session.execute(stmt)
            current_ml = res.scalar() or 0
            
            delta = water_ml - current_ml
            
            if delta > 0:
                # Approximate glasses (e.g., 250ml per glass)
                glasses = max(1, delta // 250)
                
                log_obj = DietPlanDayHydrationLog(
                    user_id=uid,
                    plan_day_id=pdid,
                    glasses=glasses,
                    volume_ml=delta,
                    source='manual'
                )
                session.add(log_obj)
                await session.commit()
            elif delta < 0:
                # We need to subtract abs(delta) from the total. 
                # We do this by deleting the most recent logs or reducing their volume.
                amount_to_remove = abs(delta)
                
                # Fetch logs ordered by most recent first
                logs_stmt = select(DietPlanDayHydrationLog).filter(
                    DietPlanDayHydrationLog.user_id == uid,
                    DietPlanDayHydrationLog.plan_day_id == pdid
                ).order_by(DietPlanDayHydrationLog.logged_at.desc())
                
                logs_res = await session.execute(logs_stmt)
                recent_logs = logs_res.scalars().all()
                
                for lg in recent_logs:
                    if amount_to_remove <= 0:
                        break
                        
                    if lg.volume_ml <= amount_to_remove:
                        # Delete the whole log
                        amount_to_remove -= lg.volume_ml
                        await session.delete(lg)
                    else:
                        # Reduce the volume of this log
                        lg.volume_ml -= amount_to_remove
                        # Update glasses approximation
                        lg.glasses = max(1, lg.volume_ml // 250)
                        amount_to_remove = 0
                
                await session.commit()
                
            return MockUserWaterLog(user_identifier, plan_day_id, water_ml)
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to save user water log to repository") from ex
