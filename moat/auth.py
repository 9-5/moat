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
async def login_form(request: Request, error: Optional[str] = None):
    """
    Serves the login form.
    """
    print(f"GET /login - Serving login form, error: {error}")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles user login.
    """
    cfg = get_settings()
    user = await authenticate_user(username, password)
    if not user:
        login_url = request.url_for("login_form").include_query_params(error="Invalid username or password")
        return RedirectResponse(url=str(login_url), status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/moat/protected-test", status_code=status.HTTP_303_SEE_OTHER)
    
    # Set the cookie
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
        path="/",
        secure=is_secure_connection_for_cookie_set,
        httponly=True,
        samesite="Lax",
        max_age=access_token_expires.total_seconds(),
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Handles user logout.  Clears the access token cookie and redirects to the URL specified in the "next" query parameter (or root if none is provided).
    """
    cfg = get_settings()
    next_url = request.query_params.get("next")
    if next_url:
        try:
            logout_redirect_target_url: str = next_url
            print(f"GET /logout - Next URL Param Provided - Redirecting to: {logout_redirect_target_url} after logout.")
        except Exception as e:
            print(f"GET /logout - Invalid 'next' URL: {next_url}.  Falling back to root.")
            logout_redirect_target_url: str = "/" #Consider a named route.
    else:
        logout_redirect_target_url: str = "/"
        print(f"GET /logout - No Next URL Param (/)- Redirecting to: {logout_redirect_target_url} after logout.")

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