from fastapi import Depends, HTTPException, status, Request, Response as FastAPIResponse # Keep FastAPIResponse for manual response construction
from typing import Optional
from urllib.parse import quote_plus, urljoin, unquote_plus

from .models import User
from .security import decode_access_token
from .database import get_user
from .config import get_settings

ACCESS_TOKEN_COOKIE_NAME = "moat_access_token"

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Retrieves the current user from the access token cookie. If no valid token 
    is found, redirects the user to the login page, preserving the original
    request URL in the 'next' query parameter.
    """
    cfg = get_settings()

    token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

    if not token:
        print(f"get_current_user_or_redirect: No token found, redirecting to login.")

        # Construct the 'next' URL, encoding the original request URL.
        current_url = request.url
        login_url = cfg.moat_base_url if cfg.moat_base_url else request.base_url # Fallback to base_url if moat_base_url not set
        next_url = quote_plus(str(current_url)) #encode original URL

        # Construct the redirect URL to the login page, including the 'next' parameter.
        redirect_url = urljoin(login_url, f"/moat/auth/login?next={next_url}")

        # Craft headers for the redirect response, including a Set-Cookie header to clear the cookie (belt and braces).
        headers = {"Location": redirect_url} # Standard redirect
        # Clear existing cookie just in case
        delete_cookie_header_val = f"{ACCESS_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if cfg.moat_base_url and cfg.moat_base_url.scheme == "https": # moat_base_url is HttpUrl type
            delete_cookie_header_val += "; Secure"
        if cfg.cookie_domain: # Add domain if configured for deletion
            delete_cookie_header_val += f"; Domain={cfg.cookie_domain}"
        headers["Set-Cookie"] = delete_cookie_header_val

        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Not authenticated, redirecting to login.",
            headers=headers
        )

    # Decode the access token to get the username.
    payload = decode_access_token(token)
    if not payload:
        print(f"get_current_user_or_redirect: Invalid token, redirecting to login.")

        current_url = request.url
        login_url = cfg.moat_base_url if cfg.moat_base_url else request.base_url
        next_url = quote_plus(str(current_url))
        redirect_url = urljoin(login_url, f"/moat/auth/login?next={next_url}")

        headers = {"Location": redirect_url}
        delete_cookie_header_val = f"{ACCESS_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if cfg.moat_base_url and cfg.moat_base_url.scheme == "https": # moat_base_url is HttpUrl type
            delete_cookie_header_val += "; Secure"
        if cfg.cookie_domain: # Add domain if configured for deletion
            delete_cookie_header_val += f"; Domain={cfg.cookie_domain}"
        headers["Set-Cookie"] = delete_cookie_header_val

        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Invalid token, redirecting to login.",
            headers=headers
        )
    
    username = payload.get("sub")
    if not username:
        print(f"get_current_user_or_redirect: No username in token, redirecting to login.")

        current_url = request.url
        login_url = cfg.moat_base_url if cfg.moat_base_url else request.base_url
        next_url = quote_plus(str(current_url))
        redirect_url = urljoin(login_url, f"/moat/auth/login?next={next_url}")

        headers = {"Location": redirect_url}
        delete_cookie_header_val = f"{ACCESS_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if cfg.moat_base_url and cfg.moat_base_url.scheme == "https": # moat_base_url is HttpUrl type
            delete_cookie_header_val += "; Secure"
        if cfg.cookie_domain: # Add domain if configured for deletion
            delete_cookie_header_val += f"; Domain={cfg.cookie_domain}"
        headers["Set-Cookie"] = delete_cookie_header_val

        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="No username in token, redirecting to login.",
            headers=headers
        )

    # Get the user from the database.
    user = await get_user(username)
    if not user:
        print(f"get_current_user_or_redirect: User '{username}' not found, redirecting to login.")

        current_url = request.url
        login_url = cfg.moat_base_url if cfg.moat_base_url else request.base_url
        next_url = quote_plus(str(current_url))
        redirect_url = urljoin(login_url, f"/moat/auth/login?next={next_url}")

        headers = {"Location": redirect_url}
        #Clear existing cookie just in case.
        delete_cookie_header_val = f"{ACCESS_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        if cfg.moat_base_url and cfg.moat_base_url.scheme == "https": # moat_base_url is HttpUrl type
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