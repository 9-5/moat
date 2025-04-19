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
    """
    Displays the login form.
    """
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles user login.
    """
    user = await authenticate_user(username, password)
    if not user:
        login_url = request.url.include_query_params(error="Invalid username or password")
        return RedirectResponse(url=str(login_url), status_code=status.HTTP_303_SEE_OTHER)

    # Create access token
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Set the cookie
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    cfg = get_settings()
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection_for_cookie_set = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie_set}")
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure_connection_for_cookie_set,
        samesite="Lax",
        domain=cookie_domain_setting,
        max_age=access_token_expires.total_seconds(),
        path="/"
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Handles user logout.  Clears the access token cookie and redirects to the root.
    """
    cfg = get_settings()
    logout_redirect_target_url = "/"

    # Sanity check -- don't allow redirects to other domains.
    if cfg.moat_base_url:
       logout_redirect_target_url = cfg.moat_base_url
       print(f"GET /logout - Redirecting to moat_base_url: {logout_redirect_target_url} after logout.")
    else:
       print(f"GET /logout - Redirecting to root (/) - Redirecting to: {logout_redirect_target_url} after logout.")

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