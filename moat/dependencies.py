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
    
    payload = decode_access_token(token)
    if payload is None:
        print("Invalid access token in cookie.")
        return None
    
    username: str = payload.get("sub")
    if username is None:
        print("Invalid subject (username) in access token.")
        return None
    
    user = User(username=username)
    print(f"User '{user.username}' found in access token.")
    return user

async def get_current_user_or_redirect(request: Request) -> User:
    user = await get_current_user_from_cookie(request)
    cfg = get_settings()
    
    if user is None:
        # Determine the "next" URL.  If moat_base_url is set, ensure it's relative to that.
        next_url = str(request.url)
        if cfg.moat_base_url:
            next_url_parsed = urlparse(next_url)
            base_url_parsed = urlparse(str(cfg.moat_base_url)) # Ensure it's a string.
            if next_url_parsed.netloc != base_url_parsed.netloc:
                print(f"Denying redirect to '{next_url}': different domain than moat_base_url '{cfg.moat_base_url}'")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid redirect target.")
        
        login_url = urljoin("/moat/auth/login", f"?next={quote_plus(next_url)}") # Already URL-encoded.

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