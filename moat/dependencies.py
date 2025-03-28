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
        
        print(f"No token found in cookie {ACCESS_TOKEN_COOKIE_NAME}, user is anonymous.")
        return None

    payload = decode_access_token(token)
    if not payload:
        print("Token is invalid.")
        return None
    
    username: str = payload.get("sub")
    if username is None:
        print("Token contains no subject (username).")
        return None
    
    user = User(username=username)
    print(f"User '{user.username}' found in token.")
    return user

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Tries to retrieve the current user from the session cookie.
    If the user is not authenticated, it redirects them to the login page,
    preserving the originally requested URL in the "next" query parameter.
    """
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)
    if user is None:
        print(f"get_current_user_or_redirect: User not authenticated, redirecting to login.")

        # Construct the URL to redirect to after login, including scheme and hostname.
        # Quote the next URL to handle special characters.
        next_url = quote_plus(str(request.url))
        login_url = urljoin(str(request.base_url), "/moat/auth/login")  # Explicitly use urljoin
        redirect_url = f"{login_url}?next={next_url}" # Manually construct the redirect URL

        print(f"Redirecting to login URL: {redirect_url}")
        headers = {"Location": redirect_url}
        #Also clear the cookie
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