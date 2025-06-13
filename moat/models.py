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
    cookie_do
... (FILE CONTENT TRUNCATED) ...

         # or specific hostname if not using subdomains for apps

    docker_monitor_enabled: bool = True
    moat_label_prefix: str = "moat"
    static_services: List[StaticServiceConfig] = []

    @field_validator('moat_base_url', mode='before')
    @classmethod
    def ensure_moat_base_url_is_str(cls, value):
        if isinstance(value, HttpUrl):
            return str(value)
        return value

    @field_validator('cookie_domain', mode='before')
    @classmethod
    def validate_cookie_domain(cls, value: Optional[str]):
        if value is not None:
            if not value.startswith('.'):
                pass
            if ' ' in value:
                raise ValueError("Cookie domain cannot contain spaces.")
        return value