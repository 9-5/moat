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
        
        print("No access token cookie found.")
        return None

    try:
        payload = decode_access_token(token)
        if payload is None or "sub" not in payload:
            print("Invalid or malformed access token.")
            return None
        username = payload.get("sub")
        print(f"Token decoded, username: {username}")
        user = User(username=username) # Don't hit the DB again here
        return user
    except Exception as e:
        print(f"Error decoding or validating token: {e}")
        return None

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Retrieves the current user from the access token cookie.
    If no valid token is found, redirects to the login page with a 'next' parameter.
    """
    user = await get_current_user_from_cookie(request)
    if user is None:
        cfg = get_settings()
        
        # URL-encode the original path to redirect back after login
        redirect_path = quote_plus(str(request.url))
        login_url = urljoin(str(cfg.moat_base_url), f"/moat/auth/login?next={redirect_path}")
        
        print(f"get_current_user_or_redirect - Not authenticated, redirecting to login at: {login_url}")
        
        # Craft a manual redirect response with a Set-Cookie header that deletes the cookie.
        headers = {"Location": login_url}

        # Craft a Set-Cookie header to delete the cookie.  Important to set attributes to match the original cookie.
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
        
    print(f"User '{user.