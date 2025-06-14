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
        print("Invalid access token found in cookie.")
        return None

    username = payload.get("sub")
    if not username:
        print("No username found in decoded access token.")
        return None

    user = await get_user(username)
    if not user:
        print(f"User '{username}' not found in database.")
        return None

    return User(username=user.username)


async def get_current_user_or_redirect(request: Request) -> User:
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)

    if not user:
        print(f"No user authenticated, redirecting to login. Request URL: {request.url}")

        # Determine the redirect target based on configuration, falling back to /login
        login_redirect_target = cfg.moat_base_url or request.base_url # Use configured base URL if available
        login_redirect_target = urljoin(str(login_redirect_target), "/moat/auth/login") # Append /login to base
        
        # Construct the "next" parameter with the *original* request URL
        next_url = quote_plus(str(request.url)) #IMPORTANT: Encode the FULL request URL
        login_redirect_url = f"{login_redirect_target}?next={next_url}"
        
        headers = {}
        # Delete the cookie if it exists (for clean redirects)
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