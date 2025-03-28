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
    """
    Authenticates a user by verifying the username and password.

    Args:
        username: The username to authenticate.
        password: The password to verify.

    Returns:
        A User object if authentication is successful, otherwise None.
    """
    user = await get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return User(username=user.username)


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request, error: str = None):
    """
    Displays the login form.

    Args:
        request: The incoming request.
        error: An optional error message to display on the form.

    Returns:
        An HTML response containing the login form.
    """
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Handles user login.

    Args:
        request: The incoming request.
        username: The username submitted in the login form.
        password: The password submitted in the login form.

    Returns:
        A redirect response to the originally requested URL upon successful login,
        or a redirect back to the login form with an error message if authentication fails.
    """
    user = await authenticate_user(username, password)
    if not user:
        # Redirect back to the login form with an error message.
        encoded_error = quote_plus("Invalid username or password")
        login_url_with_error = request.url_for("login").include_query_params(error=encoded_error)
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER)

    # Determine the originally requested URL before authentication.
    # This is stored in the "next" query parameter by the `get_current_user_or_redirect` dependency.
    next_url = request.query_params.get("next")
    if not next_url:
        # If "next" is missing, redirect to the root. This can happen if a user directly accesses /login.
        next_url = "/"

    # Create access token
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Redirect with the access token set as a cookie
    response = RedirectResponse(next_url, status_code=status.HTTP_303_SEE_OTHER)
    cfg = get_settings()
    cookie_domain_setting = cfg.cookie_domain

    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True if request.url.scheme == "https" else False,  # Send only over HTTPS
        samesite="Lax",
        domain=cookie_domain_setting,
        path="/",
        max_age=int(access_token_expires.total_seconds()),
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    """Handles user logout."""
    cfg = get_settings()
    
    # Determine the redirect target after logout.  If `moat_base_url` is configured, redirect back to it.
    # Otherwise, redirect to the root ("/").  This ensures that after logout, the user is navigated
    # back to a known URL instead of potentially a proxied service's URL which would be confusing.
    if cfg.moat_base_url:
        logout_redirect_target_url = str(cfg.moat_base_url)
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