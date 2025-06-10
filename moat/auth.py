from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from typing import Optional
from urllib.parse import quote_plus, unquote_plus, urljoin, urlparse

from pydantic import HttpUrl

from .models import User, Token
from .security import create_access_token, verify_password
from .database import get_user
from .dependencies import ACCESS_TOKEN_COOKIE_NAME
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
    Renders the login form.
    """
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles user login, sets the access token cookie, and redirects to the originally requested URL or the homepage.
    """
    user = await authenticate_user(username, password)
    if not user:
        login_url_with_error = request.url_for("login_form").include_query_params(error="Invalid username or password")
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER)

    # Create access token
    access_token = create_access_token(data={"sub": user.username})

    # Build redirect target URL.  If `next` is provided, use that, otherwise go to root.
    cfg = get_settings()
    next_url = request.query_params.get("next")
    if next_url:
        redirect_target_url = next_url
    else:
        redirect_target_url = cfg.moat_base_url if cfg.moat_base_url else "/"

    response = RedirectResponse(redirect_target_url, status_code=status.HTTP_303_SEE_OTHER) # Always use 303 for redirects after POST

    # Set the access token as a cookie
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection}")
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        domain=cookie_domain_setting,
        httponly=True,
        secure=is_secure_connection,
        samesite="Lax",
        path="/",
    )

    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Logs the user out by deleting the access token cookie and redirecting to the homepage.
    """
    cfg = get_settings()

    # Determine logout redirect target URL. If configured, use that, otherwise go to root.
    logout_redirect_target_url = cfg.moat_base_url if cfg.moat_base_url else "/"
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