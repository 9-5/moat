import sqlalchemy
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional

from .models import User, UserInDB
from .config import get_settings
from .security import get_password_hash

DATABASE_URL = None
engine = None
SessionLocal = None
Base = declarative_base()

class UserTable(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    hashed_password = Column(String)

async def init_db():
    global DATABASE_URL, engine, SessionLocal
    DATABASE_URL = get_settings().database_url.replace("sqlite+aiosqlite:///", "sqlite:///")  # SQLAlchemy requires sqlite://
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) # disable thread check for async

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_user(username: str, db: sqlalchemy.orm.Session = Depends(get_db)) -> Optional[UserInDB]:
    user = db.query(UserTable).filter(UserTable.username == username).first()
    if user:
        return UserInDB(username=user.username, hashed_password=user.hashed_password)
    return None

async def create_user_db(user_data: User, password: str, db: sqlalchemy.orm.Session = Depends(get_db)) -> UserInDB:
    hashed_password = get_password_hash(password)
    user_in_db = UserInDB(username=user_data.username, hashed_password=hashed_password)

    db_user = UserTable(username=user_data.username, hashed_password=hashed_password)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)  # Refresh to get the updated object from the DB
    except Exception as e:
        db.rollback()
        raise ValueError(f"User {user_data.username} already exists: {e}")
    return user_in_db