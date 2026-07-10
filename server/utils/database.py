from asyncpg.pool import logger
from fastapi import HTTPException
import json
import asyncpg
from config.config import get_parameter, ssm_path, DATABASE_SCHEMA


# --------------------------------------
# AWS SSM Client
# --------------------------------------

db_pool = None


# --------------------------------------
# Build DATABASE URL
# --------------------------------------
from urllib.parse import quote_plus

def build_database_url():
    user = str(get_parameter(f"{ssm_path}/DATABASE_USER")).strip()
    password = quote_plus(str(get_parameter(f"{ssm_path}/DATABASE_PASSWORD")).strip())
    host = str(get_parameter(f"{ssm_path}/DATABASE_HOST")).strip()
    port = str(get_parameter(f"{ssm_path}/DATABASE_PORT")).strip()
    name = str(get_parameter(f"{ssm_path}/DATABASE_NAME")).strip()
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = build_database_url()


# --------------------------------------
# Initialize DB Pool
# --------------------------------------

import asyncpg
import json

db_pool = None

async def init_db():
    global db_pool

    async def init_connection(conn):
        await conn.set_type_codec(
            'jsonb',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10,
        init=init_connection   # 👈 THIS IS IMPORTANT
    )

    print("✅ Database connected successfully (JSONB auto-decoding enabled)")

# --------------------------------------
# Close DB Pool
# --------------------------------------
async def close_db():
    global db_pool

    if db_pool:
        await db_pool.close()
        db_pool = None
        print("Database pool closed")




from database.session import AsyncSessionLocal
from sqlalchemy import text

async def get_user_id(user_id: str):
    """Fetch user ID from database based on email"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(f'SELECT id FROM "{DATABASE_SCHEMA}".users WHERE public_id = :public_id'),
                {"public_id": user_id}
            )
            row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        print("user", row[0])
        return str(row[0])
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching user ID for email {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching user information")