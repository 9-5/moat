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
        
        print("No access token found in cookie.  User is not authenticated.")
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        print("Invalid access token found in cookie.")
        return None
    
    username = payload.get("sub")
    if username is None:
        print("Invalid access token payload: missing subject (sub).")
        return None
    
    return User(username=username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Attempts to retrieve the current user from the access token cookie.
    If no token is present or the token is invalid, redirects to the login page.
    """
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)
    if user is None:
        # Determine the redirect URL
        # 1. Use configured login URL if available
        # 2. Otherwise, use moat_base_url + "/moat/auth/login" if moat_base_url is set
        # 3. Otherwise, use "/moat/auth/login" (relative path)

        redirect_url = "/moat/auth/login"  # Default fallback
        if cfg.moat_base_url:
            redirect_url = str(cfg.moat_base_url.join("/moat/auth/login"))
        
        #Construct full login URL with 'next' parameter
        current_url_encoded = quote_plus(str(request.url))
        login_url_with_redirect = f"{redirect_url}?next={current_url_encoded}"
        print(f"No user, redirecting to login: {login_url_with_redirect}")

        headers = {}
        # Properly delete the cookie on redirect.
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