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
        login_url = request.url_for("login_form").include_query_params(error="Invalid credentials")
        return RedirectResponse(url=str(login_url), status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    cfg = get_settings()
    
    # Determine the redirect target. Use 'next' query param if it exists, otherwise redirect to root.
    parsed_url = urlparse(str(request.url))
    query_params = dict(qc.split("=") for qc in parsed_url.query.split("&")) if parsed_url.query else {}
    next_url = query_params.get("next")
    
    if next_url:
        # Sanitize the redirect URL to prevent open redirects.
        try:
            urlparse(next_url) # Validate it's a proper URL
            redirect_target_url = next_url
            print(f"POST /login - Redirecting to 'next' URL: {redirect_target_url}")
        except:
            # If sanitization fails, redirect to root.
            redirect_target_url = "/"
            print(f"POST /login - Invalid 'next' URL, redirecting to root.")
    else:
        redirect_target_url = "/"
        print(f"POST /login - No 'next' URL, redirecting to root.")

    response = RedirectResponse(redirect_target_url, status_code=status.HTTP_303_SEE_OTHER)

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
        max_age=int(access_token_expires.total_seconds()),
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    cfg = get_settings()
    
    # Determine logout redirect target.
    parsed_url = urlparse(str(request.url))
    query_params = dict(qc.split("=") for qc in parsed_url.query.split("&")) if parsed_url.query else {}
    logout_next_url = query_params.get("next")
    
    if logout_next_url:
        try:
            urlparse(logout_next_url) # Validate it's a proper URL
            logout_redirect_target_url = logout_next_url
            print(f"GET /logout - Redirecting to 'next' URL: {logout_redirect_target_url} after logout.")
        except:
            logout_redirect_target_url = "/"
            print(f"GET /logout - Invalid 'next' URL, redirecting to root after logout.")
    else:
        logout_redirect_target_url = "/"
        print(f"GET /logout - Redirecting to root after logout.")

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