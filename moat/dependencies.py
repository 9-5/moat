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
        print(f"No access token cookie found.")
        return None

    payload = decode_access_token(token)
    if not payload:
        print(f"Invalid access token in cookie.")
        return None

    username = payload.get("sub")
    if not username:
        print(f"No username found in access token.")
        return None

    user = await get_user(username)
    if not user:
        print(f"User '{username}' not found.")
        return None
    
    print(f"User '{username}' found via cookie auth.")
    return User(username=user.username)

async def get_current_user_or_redirect(
    request: Request,
    response: FastAPIResponse,
    current_user: Optional[User] = Depends(get_current_user_from_cookie)
) -> User:
    cfg = get_settings()
    if current_user:
        return current_user

    print(f"--- Redirecting to login ---")
    print(f"No current user, redirecting to login from {request.url}")

    if cfg.moat_base_url:
      # Construct login URL with redirect
        login_url = urljoin(cfg.moat_base_url, "/moat/auth/login")
        redirect_url = str(request.url)
        encoded_redirect_url = quote_plus(redirect_url)
        full_login_url = f"{login_url}?redirect_url={encoded_redirect_url}"

        headers = {"Location": full_login_url}

        # Manually delete the cookie
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