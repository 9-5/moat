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
        print(f"No access token cookie found.")
        return None

    payload = decode_access_token(token)
    if not payload:
        print(f"Invalid or expired token in cookie.")
        return None

    username = payload.get("sub")
    if not username:
        print(f"No username found in token payload.")
        return None

    user = await get_user(username)
    if not user:
        print(f"User '{username}' not found in database.")
        return None

    print(f"User '{username}' authenticated successfully from cookie.")
    return User(username=user.username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Attempts to retrieve the current user from the access token cookie.
    If no valid token is found, redirects the user to the login page.
    """
    user = await get_current_user_from_cookie(request)
    cfg = get_settings()
    if not user:
        print(f"No valid user found, redirecting to login.")
        # Redirect to login page, preserving the originally requested URL
        #  - quote_plus is used to ensure the URL is properly encoded.
        #  - urljoin is used to combine the base URL with the path, handling cases where the base URL might or might not have a trailing slash.
        
        # Determine the base URL for Moat.  If moat_base_url is configured, use that.  Otherwise, use the request's base URL.
        if cfg.moat_base_url:
            base_url = str(cfg.moat_base_url)
        else:
            base_url = str(request.base_url)

        # Construct the full URL to redirect to after login.
        next_url = quote_plus(str(request.url))  # URL-encode the 'next' parameter
        login_url = urljoin(base_url, f"/moat/auth/login?next={next_url}")
        print(f"Redirecting to login URL: {login_url}")
        
        headers = {}
        # Add a "Set-Cookie" header to clear the access token cookie.
        # This ensures the cookie is removed, especially when the user is being redirected due to an invalid token.
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