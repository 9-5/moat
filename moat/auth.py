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
    print(f"GET /login - Rendering login form. Error: {error}")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    cfg = get_settings()

    user = await authenticate_user(username, password)
    if not user:
        login_error_url_encoded = quote_plus("Invalid username or password")
        return RedirectResponse(url=f"/moat/auth/login?error={login_error_url_encoded}", status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Determine redirect target.  If 'next' is provided and valid, use it.
    form_data = await request.form()
    next_url = form_data.get("next")
    
    if next_url:
        try:
            # Validate next_url to prevent open redirects.  Must be a relative URL or a URL
            # with the same origin as the Moat base URL.
            parsed_next_url = urlparse(next_url)
            if parsed_next_url.netloc and parsed_next_url.netloc != urlparse(str(cfg.moat_base_url)).netloc:
                print(f"POST /login - Invalid 'next' URL: {next_url}.  Ignoring.")
                next_url = None # Treat as if 'next' wasn't provided.
            else:
                print(f"POST /login - Redirecting to 'next' URL: {next_url}")
        except Exception as e:
            print(f"POST /login - Error parsing 'next' URL: {next_url}.  Ignoring.  Error: {e}")
            next_url = None
            
    if not next_url:
        next_url = "/"  # Or a default protected page

    response = RedirectResponse(next_url, status_code=status.HTTP_303_SEE_OTHER)

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
        samesite="lax",
        max_age=int(access_token_expires.total_seconds()), # Max age in seconds
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    cfg = get_settings()
    
    # Determine logout redirect target.  If moat_base_url is set, redirect there; otherwise, redirect to root.
    logout_redirect_target_url = str(cfg.moat_base_url) if cfg.moat_base_url else "/"
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