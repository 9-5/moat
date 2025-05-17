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
    """
    Displays the login form.
    """
    next_url = request.query_params.get("next") or "/"
    return templates.TemplateResponse("login.html", {"request": request, "next_url": next_url, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles user login.
    """
    user = await authenticate_user(username, password)
    cfg = get_settings()

    if not user:
        login_url_with_error = router.url_path_for("login_form") + f"?error={quote_plus('Invalid username or password')}"
        next_url = request.query_params.get("next") or "/"
        login_url_with_error += f"&next={quote_plus(next_url)}"
        return RedirectResponse(url=login_url_with_error, status_code=status.HTTP_303_SEE_OTHER)
    
    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(request.query_params.get("next") or "/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Determine if the connection is secure (HTTPS) - necessary for cookie security
    is_secure_connection = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    print(f"POST /login - Setting cookie. Domain: '{cfg.cookie_domain}', Secure: {is_secure_connection}")
    
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        domain=cfg.cookie_domain,
        path="/",
        secure=is_secure_connection,
        httponly=True,
        samesite="lax",
        expires=access_token_expires
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Handles user logout.  Deletes the access token cookie and redirects to the specified URL.
    """
    cfg = get_settings()
    logout_redirect_target_url = request.query_params.get("next") or "/"
    print(f"GET /logou