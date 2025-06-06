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
        
        print(f"No token found in cookie for {request.url}, returning None.")
        return None

    try:
        payload = decode_access_token(token)
        if payload is None:
            print(f"Token is invalid or expired, returning None.")
            return None
        username = payload.get("sub")
        if username is None:
            print(f"Token payload missing 'sub' (username), returning None.")
            return None

        return User(username=username)
    except Exception as e:
        print(f"An unexpected error occurred while decoding token: {e}")
        return None

async def get_current_user_or_redirect(request: Request) -> User:
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)
    if user is None:
        print(f"No valid user found, redirecting to login page from {request.url}.")
        
        # Construct the 'next' URL for redirecting back after login
        # Note:  We need to be careful to encode this URL so it's safe in a query parameter.
        # Without `quote_plus` spaces and special characters can break the URL or introduce vulnerabilities.
        
        current_url_path = request.url.path
        current_url_query = request.url.query

        next_url = str(request.url)

        login_url = urljoin(str(request.base_url), "/moat/auth/login") # use urljoin for safety
        
        encoded_next_url = quote_plus(next_url)  # URL-encode the next URL
        
        full_login_url = f"{login_url}?next={encoded_next_url}"
        
        print(f"Redirecting to login URL: {full_login_url}")
        
        headers = {"Location": full_login_url}

        # Manually construct the "Set-Cookie" header to delete the cookie, covering all bases.
        # This is important to ensure that if a user has an invalid cookie, it gets cleared.
        # The attributes (path, domain, secure, httponly, samesite) MUST match the original
        # cookie's attributes for the deletion to be effective.
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