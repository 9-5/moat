import aiosqlite
from typing import Optional
from .models import User, UserInDB
from .config import get_settings
from .security import get_password_hash

DATABASE_URL = None

async def get_db_connection():
    global DATABASE_URL
    if DATABASE_URL is None:
        DATABASE_URL = get_settings().database_url.replace("sqlite+aiosqlite:///", "") # aiosqlite path
    return await aiosqlite.connect(DATABASE_URL)

async def init_db():
    conn = await get_db_connection()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            hashed_password TEXT NOT NULL
        )
    """)
    await conn.commit()
    await conn.close()

async def get_user(username: str) -> Optional[UserInDB]: