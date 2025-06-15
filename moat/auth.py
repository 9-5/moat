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
    user_in_db = await get_user(username)
    if not user_in_db:
        return None
    if not verify_password(password, user_in_db.hashed_password):
        return None
    return User(username=user_in_db.username)

@router.get("/login", response_class=HTMLResponse, name="login_form_page")
async def login_form(request: Request, redirect_uri: Optional[str] = None):
    cfg = get_settings()
    moat_admin_config_path_segment = "/moat/admin/config"
    full_admin_config_url = ""

    if cfg.moat_base_url:
        moat_base_str_for_join = str(cfg.moat_base_url).rstrip('/') + '/'
        full_admin_config_url = urljoin(moat_base_str_for_join, moat_admin_config_path_segment.lstrip('/'))
    else:
        print("Warning: moat_base_url not configured, admin redirect might be relative.")
        full_admin_config_url = moat_admin_config_path_segment


    print(f"GET /login - Request URL: {request.url}")
    actual_redirect_uri_from_query = redirect_uri or request.query_params.get("redirect_uri")
    print(f"GET /login - Actual redirect_uri to consider (from query): {actual_redirect_uri_from_query}")

    current_user = await get_current_user_from_cookie(request)
    if current_user:
        print(f"GET /login - User '{current_user.username}' already logged in. Redirecting.")
        
        target_if_already_logged_in = "/"

        if actual_redirect_uri_from_query:
            target_if_already_logged_in = unquote_plus(actual_redirect_uri_from_query)
        elif request.headers.get("referer") and cfg.moat_base_url:
            try:
                referer_url_parsed = urlparse(request.headers.get("referer"))
                moat_host_from_config = urlparse(str(cfg.moat_base_url)).hostname
                if referer_url_parsed.hostname == moat_host_from_config and full_admin_config_url:
                    target_if_already_logged_in = full_admin_config_url
            except Exception as e:
                print(f"GET /login - Error parsing referer or moat_base_url: {e}")
                target_if_already_logged_in = full_admin_config_url if full_admin_config_url else "/"
        elif full_admin_config_url:
             target_if_already_logged_in = full_admin_config_url

        print(f"GET /login - Redirecting already logged-in user to: {target_if_already_logged_in}")
        return RedirectResponse(url=target_if_already_logged_in, status_code=status.HTTP_303_SEE_OTHER)
    print(f"GET /login - Showing login form. Passing redirect_uri to template: {actual_redirect_uri_from_query}")
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "redirect_uri": actual_redirect_uri_from_query
        }
    )

@router.post("/login", name="login_for_access_token")
async def login_for_access_token(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    redirect_uri: Optional[str] = Form(None) # This comes from the form's hidden input
):
    print(f"POST /login - Attempting login for user: {username}")
    print(f"POST /login - Received redirect_uri from form: {redirect_uri}")

    user = await authenticate_user(username, password)
    cfg = get_settings()

    if not cfg.moat_base_url:
        print("CRITICAL ERROR: moat_base_url is not configured in POST /login.")
        raise HTTPException(status_code=500, detail="Auth service misconfigured.")

    moat_auth_base_str = str(cfg.moat_base_url).rstrip('/')
    login_path_segment = "moat/auth/login"
    if not moat_auth_base_str.endswith('/'):
        moat_auth_base_str += '/'
    base_login_form_url = urljoin(moat_auth_base_str, login_path_segment.lstrip('/'))


    if not user:
        print(f"POST /login - Authentication failed for user: {username}")
        login_error_params = "?error=invalid_credentials"
        if redirect_uri:
            login_error_params += f"&redirect_uri={quote_plus(redirect_uri)}"
        
        failed_login_redirect_url = f"{base_login_form_url}{login_error_params}"
        print(f"POST /login - Redirecting back to login form: {failed_login_redirect_url}")
        return RedirectResponse(url=failed_login_redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    print(f"POST /login - User '{user.username}' authenticated successfully.")
    access_token_expires = timedelta(minutes=cfg.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    final_redirect_target_url_after_login: str
    if redirect_uri:
        final_redirect_target_url_after_login = unquote_plus(redirect_uri)
    else:
        moat_admin_config_path_segment = "/moat/admin/config"
        final_redirect_target_url_after_login = urljoin(moat_auth_base_str, moat_admin_config_path_segment.lstrip('/'))
        print(f"POST /login - No specific redirect_uri from form, defaulting to admin config: {final_redirect_target_url_after_login}")
    
    print(f"POST /login - Preparing to redirect to: {final_redirect_target_url_after_login}")
    successful_login_redirect = RedirectResponse(url=final_redirect_target_url_after_login, status_code=status.HTTP_303_SEE_OTHER)
    
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection_for_cookie = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Path: '/', Secure: {is_secure_connection_for_cookie}")

    successful_login_redirect.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=int(access_token_expires.total_seconds()),
        samesite="Lax",
        secure=is_secure_connection_for_cookie,
        path="/",
        domain=cookie_domain_setting
    )
    return successful_login_redirect

@router.get("/logout", name="logout_user")
async def logout(request: Request):
    cfg = get_settings()
    print(f"GET /logout - User logging out.")

    if not cfg.moat_base_url:
        print("CRITICAL ERROR: moat_base_url is not configured in GET /logout.")
        raise HTTPException(status_code=500, detail="Auth service misconfigured.")

    moat_auth_base_str = str(cfg.moat_base_url).rstrip('/')
    login_path_segment = "moat/auth/login"
    if not moat_auth_base_str.endswith('/'):
        moat_auth_base_str += '/'
    
    logout_redirect_target_url = urljoin(moat_auth_base_str, login_path_segment.lstrip('/'))
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