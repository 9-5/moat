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
        
        print(f"No token found in cookie for {request.url}")
        return None

    payload = decode_access_token(token)
    if not payload:
        print(f"Token invalid for {request.url}")
        return None

    username = payload.get("sub")
    if username is None:
        print(f"No username found in token for {request.url}")
        return None

    return User(username=username)

async def get_current_user_or_redirect(request: Request) -> User:
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)
    if user is None:
        print(f"Unauthenticated request to {request.url}, redirecting to login.")
        # Construct the full URL for the login page with a 'next' parameter.
        # The 'next' parameter should be the URL the user was trying to access.
        moat_base_url = str(cfg.moat_base_url) if cfg.moat_base_url else "/"
        next_url = quote_plus(str(request.url))  # URL-encode the 'next' URL
        login_redirect_url = urljoin(moat_base_url, f"/moat/auth/login?next={next_url}")
        
        headers = {"Location": login_redirect_url} # Set the redirect URL in the headers
        
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