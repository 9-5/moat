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
        print("Invalid or expired access token in cookie.")
        return None

    username = payload.get("sub")
    if not username:
        print("No username found in access token.")
        return None

    return User(username=username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Checks for a valid access token in the cookie.
    If found, returns the authenticated user.
    Otherwise, redirects to the login page.
    """
    user = await get_current_user_from_cookie(request)
    if user is None:
        cfg = get_settings()

        # Determine the redirect URL.  If moat_base_url is configured, use that.  Otherwise, use "/moat/auth/login"
        login_redirect_url = "/moat/auth/login"
        if cfg.moat_base_url:
            # Quote the *full* URL, so that the "next" parameter is properly encoded.
            next_url = quote_plus(str(request.url))
            login_redirect_url = urljoin(str(cfg.moat_base_url), f"/moat/auth/login?next={next_url}")
            print(f"No valid session. Redirecting to login via moat_base_url: {login_redirect_url}")
        else:
            # If no moat_base_url is provided, assume we're serving from the root.
            next_url = quote_plus(str(request.url)) # Original target URL
            login_redirect_url = f"/moat/auth/login?next={next_url}"
            print(f"No valid session. Redirecting to login: {login_redirect_url}")
        
        headers = {"Location": login_redirect_url}

        # Clear the cookie by setting it to expire immediately.
        # This is important to prevent redirect loops if the cookie is invalid.
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