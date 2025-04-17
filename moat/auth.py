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
async def login_form(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await authenticate_user(username, password)
    cfg = get_settings()

    if not user:
        login_url_with_error = request.url.include_query_params(error="Invalid credentials")
        return RedirectResponse(url=str(login_url_with_error), status_code=status.HTTP_303_SEE_OTHER)

    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection_for_cookie = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie}")
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        domain=cookie_domain_setting,
        path="/",
        secure=is_secure_connection_for_cookie,
        httponly=True,
        samesite="Lax",
        max_age=access_token_expires.total_seconds()
    )
    return response

@router.get("/logout")
async def logout(request: Request):
    cfg = get_settings()
    
    # Determine redirect target.
    logout_redirect_target_url = "/" # Default: Home page
    
    # Attempt to grab `next` query parameter. URL-decode it in case it's URL-encoded.
    if "next" in request.query_params:
        try:
            potential_redirect_url = unquote_plus(request.query_params["next"])
            urlparse(potential_redirect_url) # Validate it's a valid URL (basic check)

            # Important: Ensure the redirect target is within the service's base URL.
            # This prevents open redirect vulnerabilities.
            # This check is ONLY done if moat_base_url is set, because then Moat is acting as a gateway.
            if cfg.moat_base_url:
                print(f"GET /logout - Validating redirect target '{potential_redirect_url}' against moat_base_url: '{cfg.moat_base_url}'")
                is_valid_redirect = potential_redirect_url.startswith(str(cfg.moat_base_url))
                if is_valid_redirect:
                    logout_redirect_target_url = potential_redirect_url
                    print(f"GET /logout - Redirect target '{logout_redirect_target_url}' is valid (within moat_base_url)")
                else:
                    print(f"GET /logout - Redirect target '{potential_redirect_url}' is INVALID (outside moat_base_url), falling back to home page.")
            else:
                logout_redirect_target_url = potential_redirect_url # Allow if no moat_base_url is configured

        except Exception as e:
            print(f"GET /logout - Invalid 'next' parameter: {e}. Redirecting to home page.")

    print(f"GET /log out - Redirecting to: {logout_redirect_target_url} after logout.")

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