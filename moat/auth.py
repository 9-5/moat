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
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await authenticate_user(username, password)
    if not user:
        login_url_with_error = request.url.include_query_params(error="Invalid username or password")
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER)

    # Create access token
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Determine redirect target: 'next' query param or default to root.
    next_url = request.query_params.get("next")
    if next_url:
        # Sanitize the next URL to prevent open redirects.
        # Only allow relative URLs or URLs with the same base URL as Moat.
        try:
            parsed_next_url = urlparse(next_url)
            if parsed_next_url.netloc and (parsed_next_url.scheme != get_settings().moat_base_url.scheme or parsed_next_url.netloc != get_settings().moat_base_url.netloc):
                print(f"Login: Redirect to '{next_url}' blocked due to security concerns (different domain).")
                next_url = None  # Treat as invalid and redirect to default.
            else:
                print(f"Login: Redirecting to '{next_url}' (original 'next' parameter).")
        except Exception as e:
            print(f"Login: Error parsing 'next' URL '{next_url}': {e}.  Ignoring 'next' parameter.")
            next_url = None

    if not next_url:
        print("Login: No valid 'next' parameter, redirecting to root.")
        next_url = "/" # Default redirect.

    response = RedirectResponse(next_url, status_code=status.HTTP_303_SEE_OTHER)

    # Set the access token in a cookie.
    cookie_domain_setting = get_settings().cookie_domain
    is_secure_connection_for_cookie = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    print(f"Login: Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie}")

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure_connection_for_cookie,
        samesite="Lax",
        domain=cookie_domain_setting,
        path="/",
        max_age=int(get_settings().access_token_expire_minutes * 60)
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """Logs out the user by deleting the access token cookie."""
    cfg = get_settings()
    logout_redirect_target_url = "/" # Default

    # Honor "next" parameter (post-logout redirect) if present AND safe.
    next_url = request.query_params.get("next")
    if next_url:
        try:
            parsed_next_url = urlparse(next_url)
            # SECURITY: Only allow relative URLs or URLs with the same base URL as Moat, post-logout.
             # SECURITY: Only allow relative URLs or URLs with the same base URL as Moat.
            if parsed_next_url.netloc and (parsed_next_url.scheme != cfg.moat_base_url.scheme or parsed_next_url.netloc != cfg.moat_base_url.netloc):
                print(f"Logout: Redirect to '{next_url}' blocked due to security concerns (different domain).  Redirecting to default logout URL.")
            else:
                logout_redirect_target_url = next_url
                print(f"GET /logout - Redirecting to: {logout_redirect_target_url} after logout.")
        except Exception as e:
            print(f"Logout: Error parsing 'next' URL '{next_url}': {e}.  Redirecting to default logout URL.")

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