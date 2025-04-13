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
        print(f"No access token cookie found for {request.url}.")
        return None

    try:
        payload = decode_access_token(token)
        if payload is None:
            print(f"Invalid or expired token found in cookie for {request.url}.")
            return None

        username: str = payload.get("sub")
        if username is None:
            print(f"No username found in decoded token for {request.url}.")
            return None

        user = User(username=username)
        print(f"Successfully retrieved user '{user.username}' from cookie for {request.url}.")
        return user
    except Exception as e:
        print(f"An unexpected error occurred during token decoding: {e}")
        return None

async def get_current_user_or_redirect(request: Request) -> User:
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)
    if user is None:
        # Construct the 'next' URL parameter to redirect back after login
        current_url_quoted = quote_plus(str(request.url))
        login_url_with_redirect = urljoin(str(request.url_for("auth:login_form")), f"?next={current_url_quoted}")
        print(f"Redirecting unauthenticated user to login page: {login_url_with_redirect}")

        headers = {"Location": login_url_with_redirect}

        #Clear the cookie if it exists (logout).  Important to prevent redirect loops!
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