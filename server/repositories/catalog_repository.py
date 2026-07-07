import asyncio
from typing import List
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database.session import AsyncSessionLocal
from database.models.catalog import Cuisine
from exceptions.repository import RepositoryException

async def fetch_all_active_cuisines() -> List[Cuisine]:
    """
    Fetches all active cuisines from the database, sorted alphabetically by name.
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = (
                select(Cuisine)
                .where(Cuisine.is_active == True)
                .order_by(Cuisine.name_en.asc())
            )
            result = await session.execute(stmt)
            cuisines = result.scalars().all()
            return list(cuisines)
        except SQLAlchemyError as ex:
            raise RepositoryException("Failed to fetch cuisines") from ex
