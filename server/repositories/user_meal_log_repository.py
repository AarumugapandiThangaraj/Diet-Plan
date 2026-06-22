from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.session import AsyncSessionLocal
from database.models import DietPlanMealConsumption, DietPlanMeal, DietPlanDay, DietPlan, Meal
from sqlalchemy.exc import SQLAlchemyError
from exceptions.repository import RepositoryException
import uuid

# We create a dummy class to mock the return structure expected by V1 services
class MockUserMealLog:
    def __init__(self, user_identifier: str, meal_id: str, meal_date: date, consumed: bool, consumed_at: Optional[datetime]):
        self.user_identifier = user_identifier
        self.meal_id = meal_id
        self.meal_date = meal_date
        self.consumed = consumed
        self.consumed_at = consumed_at

async def get_meal_consumption_logs(user_identifier: str, meal_date: date) -> List[MockUserMealLog]:
    """
    Asynchronously retrieves all meal consumption logs for a user on a specific date.
    Maps from V2 DietPlanMealConsumption back to V1 mock objects.
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
            except ValueError:
                return []
                
            stmt = (
                select(DietPlanMealConsumption)
                .join(DietPlanMeal)
                .join(Meal)
                .filter(
                    DietPlanMealConsumption.user_id == uid,
                    DietPlanMealConsumption.consumed_date == meal_date
                )
                .options(selectinload(DietPlanMealConsumption.plan_meal).selectinload(DietPlanMeal.meal))
            )
            res = await session.execute(stmt)
            consumptions = res.scalars().all()
            
            out = []
            for c in consumptions:
                # Get the string client_meal_id
                client_meal_id = "UNKNOWN"
                if c.plan_meal and c.plan_meal.meal:
                    client_meal_id = c.plan_meal.meal.client_meal_id
                
                out.append(MockUserMealLog(
                    user_identifier=user_identifier,
                    meal_id=client_meal_id,
                    meal_date=c.consumed_date,
                    consumed=c.state in ('eaten', 'partial'),
                    consumed_at=c.consumed_at
                ))
            return out
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to load user meal logs from repository") from ex

async def save_meal_consumption_log(
    user_identifier: str,
    meal_id: str,
    meal_date: date,
    consumed: bool
) -> MockUserMealLog:
    """
    Asynchronously upserts a user meal consumption log.
    Finds the active DietPlanMeal matching the meal_id and meal_date, and updates DietPlanMealConsumption.
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
            except ValueError:
                raise RepositoryException("Invalid user identifier format (expected UUID)")
            
            # Find the active plan meal
            stmt = (
                select(DietPlanMeal)
                .join(DietPlanDay)
                .join(DietPlan)
                .join(Meal)
                .filter(
                    DietPlan.user_id == uid,
                    DietPlan.status == 'active',
                    Meal.client_meal_id == meal_id
                    # Ideally filter by date too, but V1 just passed meal_id. We take the first match.
                )
            )
            res = await session.execute(stmt)
            plan_meal = res.scalars().first()
            
            if not plan_meal:
                raise RepositoryException(f"Meal {meal_id} not found in active plan for user {user_identifier}")
                
            # Check for existing consumption
            c_stmt = select(DietPlanMealConsumption).filter_by(
                user_id=uid,
                plan_meal_id=plan_meal.id
            )
            c_res = await session.execute(c_stmt)
            c_obj = c_res.scalar_one_or_none()
            
            now = datetime.utcnow()
            state = 'eaten' if consumed else 'skipped'
            
            if not c_obj:
                c_obj = DietPlanMealConsumption(
                    user_id=uid,
                    plan_meal_id=plan_meal.id,
                    state=state,
                    consumed_at=now if consumed else None,
                    consumed_date=meal_date
                )
                session.add(c_obj)
            else:
                c_obj.state = state
                c_obj.consumed_at = now if consumed else None
                c_obj.consumed_date = meal_date
                
            await session.commit()
            
            return MockUserMealLog(
                user_identifier=user_identifier,
                meal_id=meal_id,
                meal_date=meal_date,
                consumed=consumed,
                consumed_at=c_obj.consumed_at
            )
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to save user meal log to repository") from ex
