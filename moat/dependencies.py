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
        
        print("No access token found in cookie, user is not authenticated.")
        return None
    try:
        payload = decode_access_token(token)
        if payload is None or "sub" not in payload:
            print("Invalid or malformed access token.")
            return None

        username = payload["sub"]
        return User(username=username)
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Retrieves the current user from the access token cookie. If no valid token exists,
    redirects the user to the login page.
    """
    user = await get_current_user_from_cookie(request)
    if user is None:
        print(f"Unauthenticated user attempting to access {request.url}, redirecting to login.")
        cfg = get_settings()
        #Construct the full URL to redirect to, including the original path.
        login_url = "/moat/auth/login"
        if cfg.moat_base_url:
             login_url = str(cfg.moat_base_url.join_url("/moat/auth/login"))
             #login_url = urljoin(str(cfg.moat_base_url), "/moat/auth/login")
        
        # URL-encode the 'next' parameter
        next_url = str(request.url)
        encoded_next_url = quote_plus(next_url)

        # Construct the redirect URL with the 'next' parameter
        redirect_url = f"{login_url}?next={encoded_next_url}"
        
        headers = {}

        # Clear the cookie during redirection to login
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