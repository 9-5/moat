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
    print(f"GET /login - Rendering login form, error: {error}")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    cfg = get_settings()
    user = await authenticate_user(username, password)
    if not user:
        login_url_with_error = request.url.include_query_params(error="Invalid username or password")
        print(f"POST /login - Authentication failed for user '{username}', redirecting back to login form with error.")
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Determine the redirect target.  If 'next' is provided, use it.  Otherwise, redirect to moat_base_url.
    form_data = await request.form()
    next_url = form_data.get("next")
    if next_url:
        login_redirect_target_url = next_url
        print(f"POST /login - 'next' parameter found: '{next_url}'.  Redirecting to '{login_redirect_target_url}' after login.")
    elif cfg.moat_base_url:
        login_redirect_target_url = str(cfg.moat_base_url) # Redirect to moat_base_url if set.
        print(f"POST /login - No 'next' parameter, redirecting to moat_base_url: '{login_redirect_target_url}' after login.")
    else:
        login_redirect_target_url = "/" #Or perhaps raise an exception if moat_base_url isn't configured?
        print(f"POST /login - No 'next' parameter, and no moat_base_url configured. Redirecting to '/' after login.")

    response = RedirectResponse(login_redirect_target_url, status_code=status.HTTP_303_SEE_OTHER)
    
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection_for_cookie_set = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie_set}")

    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        domain=cookie_domain_setting,
        httponly=True,
        secure=is_secure_connection_for_cookie_set,
        samesite="Lax",
        max_age=cfg.access_token_expire_minutes * 60,  # Convert minutes to seconds
        path="/",
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    cfg = get_settings()
    # Determine the redirect target.  If moat_base_url is provided, use it.  Otherwise, redirect to root.
    if cfg.moat_base_url:
        logout_redirect_target_url = str(cfg.moat_base_url) # Redirect to moat_base_url if set.
        print(f"GET /logout - Redirecting to moat_base_url: {logout_redirect_target_url} after logout.")
    else:
        logout_redirect_target_url = "/"
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