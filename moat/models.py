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
    listen_port: int = 8000
    secret_key: str
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite+aiosqlite:///./moat.db"
    
    moat_base_url: HttpUrl # Public URL for Moat's auth pages, e.g., https://moat.yourdomain.com
    cookie_domain: str = None # e.g., .yourdomain.com for SSO across subdomains
         # or specific hostname if not using subdomains for apps

    docker_monitor_enabled: bool = True
    moat_label_prefix: str = "moat"
    static