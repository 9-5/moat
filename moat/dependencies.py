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
        print(f"No access token cookie found for {request.url}")
        return None

    try:
        payload = decode_access_token(token)
        if payload is None:
            print(f"Invalid access token found in cookie for {request.url}")
            return None
        username = payload.get("sub")
        if username is None:
            print(f"No username found in access token for {request.url}")
            return None
        return User(username=username)
    except Exception as e:
        print(f"Error decoding access token: {e}")
        return None

async def get_current_user_or_redirect(request: Request) -> User:
    user = await get_current_user_from_cookie(request)
    cfg = get_settings()
    
    if user is None:
        print(f"No user authenticated, redirecting to login from {request.url}")
        
        # Determine the login redirect target URL.
        login_redirect_target_url = request.url
        if cfg.moat_base_url:
            # If moat_base_url is set, construct an absolute URL.
            login_redirect_target_url = urljoin(str(cfg.moat_base_url), request.url.path)

        # Quote the URL to handle special characters correctly.
        quoted_login_redirect_target_url = quote_plus(str(login_redirect_target_url))
        
        headers = {}
        
        # Build correct redirect URL including the "next" parameter
        login_url = request.url_for("login_form")
        redirect_url_with_next = login_url.include_query_params(next=quoted_login_redirect_target_url)
        
        # Construct header value for cookie deletion
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