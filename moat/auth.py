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

async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: str = None):
    """Displays the login form."""
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), next_url: str = Form(None)):
    """Handles user login."""
    user = await authenticate_user(username, password)
    if not user:
        # Quote the plus sign to prevent it from being replaced with a space.
        error_message = quote_plus("Invalid username or password")
        login_url_with_error = request.url_for("login_form").include_query_params(error=error_message)

        # Redirect back to the login form with an error message
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    # Construct redirect target
    cfg = get_settings()
    redirect_target = cfg.moat_base_url
    if next_url:
        redirect_target = next_url
    
    # Create Response (FastAPI) and set cookie
    response = RedirectResponse(redirect_target, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure= cfg.moat_base_url.scheme == "https", # Only set secure flag if using HTTPS
        domain=cfg.cookie_domain,
        path="/",
    )

    return response

@router.get("/logout")
async def logout(request: Request, next_url: str = None):
    """Handles user logout by deleting the access token cookie."""
    cfg = get_settings()
    # Determine the logout redirect target:
    # 1. If `next_url` is provided as a query parameter, use it.
    # 2. Otherwise, redirect to the Moat base URL.
    logout_redirect_target_url = next_url if next_url else str(cfg.moat_base_url)

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