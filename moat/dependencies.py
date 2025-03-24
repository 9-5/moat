from fastapi import Depends, HTTPException, status, Request, Response as FastAPIResponse # Keep FastAPIResponse for manual response construction
from typing import Optional
from urllib.parse import quote_plus, urljoin, unquote_plus

from .models import User
from .security import decode_access_token
from .database import get_user
from .config import get_settings

ACCESS_TOKEN_COOKIE_NAME = "moat_access_token"

async def get_current_user_from_cookie(request: Request) -> Optional[User]:
    print(f"--- Cookie Auth Debug ---")
    print(f"Attempting to get user from cookie for request to: {request.url}")
    print(f"All Request Cookies: {request.cookies}")
    
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        
        print(f"No token found in cookie. Returning None.")
        return None

    payload = decode_access_token(token)
    if payload is None:
        print(f"Invalid token found in cookie. Returning None.")
        return None

    username: str = payload.get("sub")
    if username is None:
        print(f"No username found in token payload. Returning None.")
        return None
    
    user = User(username=username)
    print(f"User '{user.username}' authenticated from cookie.")
    return user

async def get_current_user_or_redirect(request: Request, response: FastAPIResponse = None, current_user: Optional[User] = Depends(get_current_user_from_cookie)) -> User:
    """
    Tries to get the current user from the cookie. If not authenticated,
    redirects to the login page, preserving the original URL as a redirect parameter.
    """
    cfg = get_settings()
    print(f"--- Auth Check ---")
    print(f"Checking authentication for request to: {request.url}")
    
    if current_user:
        print(f"User '{current_user.username}' already authenticated, proceeding with request.")
        return current_user
    
    print(f"No user authenticated, redirecting to login.")
    
    if cfg.moat_base_url:
        login_url = urljoin(str(cfg.moat_base_url), "/moat/auth/login")
    else:
        login_url = "/moat/auth/login"

    # Construct redirect URL, encoding the *original* request URL.
    redirect_url = quote_plus(str(request.url))
    login_url_with_redirect = f"{login_url}?redirect_url={redirect_url}"

    headers = {"Location": login_url_with_redirect} # Set redirect URL

    # Must clear cookie explicitly when redirecting - FastAPI/Starlette doesn't always do it automatically.
    # Adapted from Auth.py - aims to be as careful as possible with cookie domain/secure/etc.
    delete_cookie_header_val = f"{ACCESS_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if cfg.moat_base_url.scheme == "https": # moat_base_url is HttpUrl type
            delete_cookie_header_val += "; Secure"
        if cfg.cookie_domain: # Add domain if configured for deletion
            delete_cookie_header_val += f"; Domain={cfg.cookie_domain}"
        headers["Set-Cookie"] = delete_cookie_header_val

        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Not authenticated, redirecting to login.",
            headers=headers
        )
        
    print(f"User '{user.username}' authenticated successfully for {request.url}, proceeding with request.")
    return user