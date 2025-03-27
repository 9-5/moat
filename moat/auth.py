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
    """Displays the login form."""
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Handles user login."""
    user = await authenticate_user(username, password)
    if not user:
        # Quote the username and password in the URL to prevent any URL parsing issues
        error_message = "Invalid username or password"
        login_url = request.url.include_query_params(error=error_message)
        return RedirectResponse(url=str(login_url), status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    cookie_domain_setting = get_settings().cookie_domain
    is_secure_connection_for_cookie = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie}")

    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure_connection_for_cookie,
        samesite="Lax",
        domain=cookie_domain_setting,
        path="/",
        max_age=int(access_token_expires.total_seconds()),
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """Handles user logout."""
    cfg = get_settings()
    
    # Determine the redirect target after logout.  If `moat_base_url` is configured, redirect back to it.
    # Otherwise, redirect to the root ("/").  This ensures that after logout, the user is navigated
    # back to a known URL instead of potentially a proxied service's URL which would be confusing.
    if cfg.moat_base_url:
        logout_redirect_target_url = str(cfg.moat_base_url)
    else:
        logout_redirect_target_url = "/"

    print(f"GET /log