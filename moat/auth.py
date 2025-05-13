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
async def login_form(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await authenticate_user(username, password)
    if not user:
        login_url = request.url_for("login_form")
        error_url = f"{login_url}?error={quote_plus('Invalid username or password')}"
        return RedirectResponse(url=error_url, status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    cfg = get_settings()
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER) # Redirect to root
    
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection}")
    
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure_connection,
        samesite="Lax",
        domain=cookie_domain_setting,
        path="/",
        max_age=access_token_expires.total_seconds()
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Logs the user out by clearing the access token cookie.
    """
    cfg = get_settings()

    # Determine the target URL for redirection after logout.
    # If moat_base_url is configured, use it to construct the absolute URL; otherwise, redirect to root ("/").
    if cfg.moat_base_url:
        logout_redirect_target_url = str(cfg.moat_base_url)  # Use moat_base_url as a HttpUrl
        parsed_url = urlparse(logout_redirect_target_url)
        if not parsed_url.path or parsed_url.path == "/":
            logout_redirect_target_url = urljoin(logout_redirect_target_url, "/")
        
    else:
        logout_redirect_target_url = "/" # Redirect to root if moat_base_url is not set

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