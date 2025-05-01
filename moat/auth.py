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
    """Returns the login form."""
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authenticates the user and sets the access token cookie."""
    user = await authenticate_user(username, password)
    if not user:
        # Redirect back to login with an error message
        login_url_with_error = request.url_for("login_form").include_query_params(error="Invalid username or password")
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER)

    cfg = get_settings()
    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/moat/protected-test", status_code=status.HTTP_303_SEE_OTHER) # Redirect to protected test route

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
        secure=is_secure_connection_for_cookie_set, # Only allow on HTTPS
        samesite="Lax",
        domain=cookie_domain_setting,
        path="/",
        max_age=access_token_expires.total_seconds()
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """Logs the user out by deleting the access token cookie."""
    cfg = get_settings()
    # Determine redirect target
    moat_base_url = cfg.moat_base_url
    if moat_base_url:
        # moar_base_url is defined, redirect there after logout
         logout_redirect_target_url = str(moat_base_url)
    else:
        # if not defined redirect to "/"
        logout_redirect_target_url = "/" # Redirect to root if no moat_base_url specified
    print(f"GET /log