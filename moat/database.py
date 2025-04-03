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
    
... (FILE CONTENT TRUNCATED) ...
   await conn.close()
    if row:
        return UserInDB(username=row[0], hashed_password=row[1])
    return None

async def create_user_db(user_data: User, password: str) -> UserInDB:
    hashed_password = get_password_hash(password)
    user_in_db = UserInDB(username=user_data.username, hashed_password=hashed_password)

    conn = await get_db_connection()
    try:
        await conn.execute(
            "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
            (user_in_db.username, user_in_db.hashed_password)
        )
        await conn.commit()
    except aiosqlite.IntegrityError:
        await conn.close()
        raise ValueError(f"User {user_data.username} already exists")
    await conn.close()
    return user_in_db