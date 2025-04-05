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
        print(f"No token found in cookie '{ACCESS_TOKEN_COOKIE_NAME}'.")
        return None

    payload = decode_access_token(token)
    if payload is None:
        print("Token is invalid.")
        return None
    username = payload.get("sub")
    if username is None:
        print("Token contains no subject (username).")
        return None

    return User(username=username)


async def get_current_user_or_redirect(request: Request) -> User:
    """
    Authenticates user via cookie.  Redirects to login if not authenticated.
    """
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)
    if user is None:
        print("User not authenticated, redirecting to login.")
        # Determine the 'next' URL
        current_url_str = str(request.url)
        login_redirect_url = urljoin(str(request.base_url), "/moat/auth/login")
        
        # Construct the 'next' parameter for the login URL, ensuring double URL encoding
        double_encoded_current_url = quote_plus(quote_plus(current_url_str)) # Double encode the URL

        #Construct final redirect URL
        final_redirect_url = f"{login_redirect_url}?next={double_encoded_current_url}"
        print(f"Redirecting to login with 'next' URL: {final_redirect_url}")
        
        headers = {}
        # Set delete cookie header to clear potentially invalid cookies
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