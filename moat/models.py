from pydantic import BaseModel, HttpUrl, field_validator # Import field_validator
from typing import Optional, Dict, List

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str

class UserInDB(User):
    hashed_password: str

class StaticServiceConfig(BaseModel):
    hostname: str
    target_url: HttpUrl

class MoatSettings(BaseModel):
    listen_host: str = "0.0.0.0"
    listen_port: int = 8