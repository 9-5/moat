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
        # Quote the plus sign to avoid it being converted to a space
        login_url_with_error = request.url_for("login_form").include_query_params(error=quote_plus("Invalid username or password"))
        print(f"POST /login - Authentication failure for user '{username}'. Redirecting back to login with error.")
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER)
    
    cfg = get_settings()
    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    is_secure_connection = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    print(f"POST /login - Setting cookie. Domain: '{cfg.cookie_domain}', Secure: {is_secure_connection}")

    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure_connection,
        samesite="lax",
        domain=cfg.cookie_domain, # Use configured cookie domain
        path="/"
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """Handles user logout."""
    cfg = get_settings()
    
    # Determine the target URL after logout.
    logout_redirect_target_url = "/"  # Default to the homepage.
    if cfg.moat_base_url:
        # If moat_base_url is set, construct an absolute URL.
        logout_redirect_target_url = str(cfg.moat_base_url)
    
    print(f"GET /log