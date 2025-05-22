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
    """
    Displays the login form.

    Args:
        request (Request): The incoming request.
        error (str, optional): An error message to display. Defaults to None.
    """
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles user login.

    Args:
        request (Request): The incoming request.
        username (str, optional): The username from the form.
        password (str, optional): The password from the form.

    Raises:
        HTTPException: Returns a 401 Unauthorized error if authentication fails.

    Returns:
        RedirectResponse: Redirects to the originally requested URL or the default redirect URL on successful login.
    """
    user = await authenticate_user(username, password)
    if not user:
        login_url_with_error = request.url_for("login_form").include_query_params(error="Invalid username or password")
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER) # Redirect back to login form

    cfg = get_settings()
    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Determine redirect target
    original_url = request.cookies.get("original_url")
    redirect_target_url = original_url if original_url else cfg.default_redirect_url
    if not redirect_target_url:
        redirect_target_url = "/"  # Or some other default if original_url is missing and default_redirect_url is not set.

    response = RedirectResponse(redirect_target_url, status_code=status.HTTP_303_SEE_OTHER) # Use 303 See Other

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
        max_age=access_token_expires.total_seconds()
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Handles user logout.  Deletes the access token cookie and redirects to the Moat base URL.
    If a 'redirect_url' is provided as a query parameter, the user will be redirected there after logout.

    Args:
        request (Request): The incoming request.

    Returns:
        RedirectResponse: Redirects to the specified URL after logout.
    """
    cfg = get_settings()
    logout_redirect_target_url = cfg.moat_base_url if cfg.moat_base_url else "/"

    # Check for a redirect_url parameter in the query string.  If present, use it.
    if "redirect_url" in request.query_params:
        logout_redirect_target_url = request.query_params["redirect_url"]
        print(f"GET /logout - redirect_url parameter found: '{logout_redirect_target_url}'")

    print(f"GET /log