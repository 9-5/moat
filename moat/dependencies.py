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
        print("No access token found in cookie.")
        return None

    payload = decode_access_token(token)
    if not payload:
        print("Invalid or expired access token.")
        return None

    username = payload.get("sub")
    if not username:
        print("No username found in access token.")
        return None

    return User(username=username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Retrieves the current user from the access token cookie.

    If the user is not authenticated (no valid access token), this dependency
    raises an HTTP 302 redirect to the login page.
    """
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)

    if user is None:
        print(f"No valid user found, redirecting to login.")
        headers = {"Location": "/moat/auth/login"} # Redirect to login

        # Construct the 'next' URL, encoding the current URL
        current_url_str = str(request.url)
        encoded_next_url = quote_plus(current_url_str)
        login_url_with_redirect = f"/moat/auth/login?next={encoded_next_url}"

        # Check if login URL is overridden in config
        if cfg.login_url:
            login_url_with_redirect = cfg.login_url
            print(f"Custom login url detected, redirecting to {login_url_with_redirect}")

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