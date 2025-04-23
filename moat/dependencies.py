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
        print(f"No token found in cookie.  Returning None")
        return None

    payload = decode_access_token(token)
    if not payload:
        print("Invalid token found in cookie. Returning None.")
        return None

    username = payload.get("sub")
    if not username:
        print("No username found in token payload. Returning None")
        return None

    return User(username=username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Authenticates the user based on the access token cookie.
    If the user is authenticated, returns the User object.
    Otherwise, redirects to the login page with a 'next' parameter indicating the originally requested URL.
    """
    user = await get_current_user_from_cookie(request)
    if user is None:
        print("No valid user found in cookie. Redirecting to login.")

        cfg = get_settings()
        # URL-encode the original URL to ensure it's correctly passed as a query parameter.
        # next_url = quote_plus(str(request.url)) # Encode the entire URL

        # next_url = str(request.url) # str() already URL encodes unsafe characters.  Don't double encode!

        # Determine the appropriate login redirect target
        login_redirect_target_url = cfg.moat_base_url.include_query_params(next=str(request.url))
    
        headers = {}
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