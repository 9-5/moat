from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from typing import Optional
from urllib.parse import quote_plus, unquote_plus, urljoin, urlparse

from pydantic import HttpUrl

from .models import User
from .security import create_access_token, verify_password
from .database import get_user
from .dependencies import ACCESS_TOKEN_COOKIE_NAME, get_current_user_from_cookie
from .config import get_settings

router = APIRouter(prefix="/moat/auth", tags=["authentication"])
templates = Jinja2Templates(directory="moat/templates")

async def authenticate_user(username: str, password: str) -> Optional[User]:
    user = await get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return User(username=user.username)

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: str = None):
    cfg = get_settings()
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "moat_base_url": str(cfg.moat_base_url) if cfg.moat_base_url else "/"})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    cfg = get_settings()
    user = await authenticate_user(username, password)
    if not user:
        login_error_url = request.url.include_query_params(error="Invalid username or password")
        return RedirectResponse(url=str(login_error_url), status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Determine if the connection is secure for cookie settings
    is_secure_connection = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    
    response = RedirectResponse(url="/moat/protected-test", status_code=status.HTTP_303_SEE_OTHER) # Redirect to a protected test endpoint, or root "/"
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure_connection,
        samesite="lax",
        max_age=access_token_expires.total_seconds(),
        domain=cfg.cookie_domain, # Use configured cookie domain, or None if not set
        path="/",
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    cfg = get_settings()
    moat_base_url = str(cfg.moat_base_url) if cfg.moat_base_url else "/"
    logout_redirect_target_url = urljoin(moat_base_url, "/") 
    print(f"GET /logout - Redirecting to: {logout_redirect_target_url} after logout.")

    response = RedirectResponse(url=logout_redirect_target_url, status_code=status.HTTP_303_SEE_OTHER)
    
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection_for_cookie_delete = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    print(f"GET /logout - Deleting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie_delete}")

    response.delete_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        path="/",
        domain=cookie_domain_setting,
        secure=is_secure_connection_for_cookie_delete,
        httponly=True,
        samesite="Lax"
    )
    return response