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

async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticates a user against the database."""
    user = await get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: str = None):
    """Displays the login form."""
    cfg = get_settings()
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "moat_base_url": cfg.moat_base_url})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Handles user login."""
    user = await authenticate_user(username, password)
    if not user:
        # Failed authentication: Redirect back to login form with an error message.
        error_message = "Invalid username or password"
        encoded_error_message = quote_plus(error_message)  # URL-encode the error message

        # Build the redirect URL, including the encoded error message.
        login_url = request.url_for("login_form")  # Correctly generate the URL for the login_form endpoint
        redirect_url = f"{login_url}?error={encoded_error_message}"  # Append the encoded error to the URL

        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    # Successful authentication: Create access token and set cookie.
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    cfg = get_settings()
    is_secure_connection = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    response = RedirectResponse("/", status_code=status.HTTP_302_FOUND) # Redirect to root.
    print(f"POST /login - Setting cookie. Domain: '{cfg.cookie_domain}', Secure: {is_secure_connection}")

    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure_connection,
        samesite="lax",
        domain=cfg.cookie_domain, # Use configured cookie domain
        path="/"
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """Handles user logout."""
    cfg = get_settings()
    
    # Determine the target URL after logout.
    logout_redirect_target_url = "/"  # Default to the homepage.
    if cfg.moat_base_url:
        # If moat_base_url is set, construct an absolute URL.
        logout_redirect_target_url = str(cfg.moat_base_url)
    
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