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
    """
    Authenticates a user against the database.
    """
    user = await get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return User(username=user.username)

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: str = None):
    """
    Displays the login form.
    """
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles user login.
    """
    cfg = get_settings()
    user = await authenticate_user(username, password)
    if not user:
        # Show the login form again with an error message
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})

    # Create access token
    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Determine the redirect target
    parsed_url = urlparse(str(request.base_url)) # str() to convert URL object to string
    login_redirect_target_url = urljoin(str(cfg.moat_base_url), "/") if cfg.moat_base_url else "/"
    print(f"POST /login - Redirecting to: {login_redirect_target_url} after login.")

    # Set the access token in a cookie and redirect
    response = RedirectResponse(login_redirect_target_url, status_code=status.HTTP_303_SEE_OTHER)
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection_for_cookie = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie}")

    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        domain=cookie_domain_setting,
        path="/",
        secure=is_secure_connection_for_cookie,
        httponly=True,
        samesite="Lax",
        max_age=int(access_token_expires.total_seconds()),
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Handles user logout.
    """
    cfg = get_settings()

    # Determine the redirect target after logout
    parsed_url = urlparse(str(request.base_url))  # Ensure base_url is a string
    logout_redirect_target_url = urljoin(str(cfg.moat_base_url), "/") if cfg.moat_base_url else "/"
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