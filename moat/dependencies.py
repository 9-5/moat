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
        print(f"No token found in cookie.")
        return None

    payload = decode_access_token(token)
    if not payload:
        print(f"Invalid token found in cookie.")
        return None

    username = payload.get("sub")
    if not username:
        print(f"No username found in token payload.")
        return None

    user = await get_user(username)
    if not user:
        print(f"User not found: {username}")
        return None
    
    return User(username=user.username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Retrieves the current user from the access token cookie.

    If the user is not authenticated (no valid token), it redirects to the login page.
    """
    user = await get_current_user_from_cookie(request)
    cfg = get_settings()

    if user is None:
        print("No valid user found, redirecting to login.")
        # Determine the login URL, including the original path as a redirect target
        # quote_plus is used to safely encode the URL for use in the query parameter
        safe_redirect_url = quote_plus(str(request.url))
        login_url = urljoin(str(cfg.moat_base_url or request.base_url), "/moat/auth/login") # Use explicitly configured moat_base_url, else request.base_url

        redirect_url_with_query_param = f"{login_url}?next={safe_redirect_url}"
        headers = {"Location": redirect_url_with_query_param}

        # Manually construct the "Set-Cookie" header to delete the cookie
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