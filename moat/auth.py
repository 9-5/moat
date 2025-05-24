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
    cfg = get_settings()
    original_url = request.query_params.get("redirect_url")
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "original_url": original_url,
        "moat_base_url": cfg.moat_base_url
    })

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    cfg = get_settings()
    user = await authenticate_user(username, password)
    if not user:
        # Re-render the login form with an error message
        form_url = request.url_for("login_form")
        encoded_error = quote_plus("Invalid username or password")
        error_url = f"{form_url}?error={encoded_error}"
        if "redirect_url" in request.query_params:
             error_url += f"&redirect_url={quote_plus(request.query_params['redirect_url'])}"

        return RedirectResponse(url=error_url, status_code=status.HTTP_303_SEE_OTHER)

    # Create access token
    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Determine the redirect URL.  If there is a redirect_url in the query params, use it.
    # otherwise use the default_redirect_url from the config, or just redirect to /
    redirect_url = cfg.default_redirect_url
    if "redirect_url" in request.query_params:
        redirect_url = request.query_params["redirect_url"]
    if not redirect_url:
        redirect_url = "/"
    print(f"POST /login - redirecting to: '{redirect_url}'")

    # Set the cookie and redirect
    response = RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure= (request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"),
        samesite="Lax",
        domain=cfg.cookie_domain, # Only set domain if configured.
        path="/",
        max_age=access_token_expires.total_seconds()
    )

    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Logs out the user by deleting the access token cookie and redirects to the Moat base URL.
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