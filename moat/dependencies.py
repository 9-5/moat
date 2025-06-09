from fastapi import Depends, HTTPException, status, Request, Response as FastAPIResponse # Keep FastAPIResponse for manual response construction
from typing import Optional
from urllib.parse import quote_plus, urljoin, unquote_plus

from .models import User
from .security import decode_access_token
from .database import get_user
from .config import get_settings

ACCESS_TOKEN_COOKIE_NAME = "moat_access_token"

# REMOVING GET_CURRENT_USER_FROM_COOKIE - no longer used directly. Logic moved into get_current_user_or_redirect

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Retrieves the current user from the access token cookie. If no valid token 
    is found, redirects the user to the login page, preserving the originally 
    requested URL for redirection after successful login.
    """
    cfg = get_settings()
    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    if not token:
        print(f"No token cookie found, redirecting to login: {request.url}")

        # URL-encode the original path so that the login page can redirect back
        login_redirect_url_encoded = quote_plus(str(request.url))
        
        # Construct the full login URL with the 'next' parameter
        login_url = f"/moat/auth/login?next={login_redirect_url_encoded}"
        
        # Return an HTTP exception that contains a redirect in the headers.
        # This is a workaround for FastAPI not directly supporting redirects within dependencies.

        headers = {"Location": login_url}

        # Added delete cookie header on redirect to login (belt and braces).
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

    payload = decode_access_token(token)
    if payload is None:
        print(f"Invalid token found, redirecting to login: {request.url}")

        login_redirect_url_encoded = quote_plus(str(request.url))
        login_url = f"/moat/auth/login?next={login_redirect_url_encoded}"
        headers = {"Location": login_url}
        
        # Added delete cookie header on redirect to login (belt and braces).
        delete_cookie_header_val = f"{ACCESS_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if cfg.moat_base_url.scheme == "https": # moat_base_url is HttpUrl type
            delete_cookie_header_val += "; Secure"
        if cfg.cookie_domain: # Add domain if configured for deletion
            delete_cookie_header_val += f"; Domain={cfg.cookie_domain}"
        headers["Set-Cookie"] = delete_cookie_header_val
        
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Invalid token, redirecting to login.",
            headers=headers
        )

    username = payload.get("username")
    if username is None:
        print("No username found in token, redirecting to login.")

        login_redirect_url_encoded = quote_plus(str(request.url))
        login_url = f"/moat/auth/login?next={login_redirect_url_encoded}"
        headers = {"Location": login_url}

        # Added delete cookie header on redirect to login (belt and braces).
        delete_cookie_header_val = f"{ACCESS_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if cfg.moat_base_url.scheme == "https": # moat_base_url is HttpUrl type
            delete_cookie_header_val += "; Secure"
        if cfg.cookie_domain: # Add domain if configured for deletion
            delete_cookie_header_val += f"; Domain={cfg.cookie_domain}"
        headers["Set-Cookie"] = delete_cookie_header_val

        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="No username in token, redirecting to login.",
            headers=headers
        )

    user = await get_user(username)
    if user is None:
        print(f"User '{username}' not found, redirecting to login.")

        login_redirect_url_encoded = quote_plus(str(request.url))
        login_url = f"/moat/auth/login?next={login_redirect_url_encoded}"
        headers = {"Location": login_url}

        # Added delete cookie header on redirect to login (belt and braces).
        delete_cookie_header_val = f"{ACCESS_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if cfg.moat_base_url.scheme == "https": # moat_base_url is HttpUrl type
            delete_cookie_header_val += "; Secure"
        if cfg.cookie_domain: # Add domain if configured for deletion
            delete_cookie_header_val += f"; Domain={cfg.cookie_domain}"
        headers["Set-Cookie"] = delete_cookie_header_val

        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail=f"User '{username}' not found, redirecting to login.",
            headers=headers
        )
    
    return User(username=user.username) # Return a simple User object