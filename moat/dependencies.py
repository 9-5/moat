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
        print(f"Cookie '{ACCESS_TOKEN_COOKIE_NAME}' not found in request.")
        print(f"-------------------------")
        return None
    
    if not isinstance(token, str):
        print(f"Cookie '{ACCESS_TOKEN_COOKIE_NAME}' value is not a string: {type(token)}")
        print(f"-------------------------")
        return None

    print(f"Found token: {token[:30]}...{token[-30:] if len(token) > 60 else token[30:]}")

    payload = decode_access_token(token)
    if payload is None:
        print(f"Token decoding failed or token is invalid (decode_access_token returned None).")
        print(f"-------------------------")
        return None
    print(f"Token payload successfully decoded: {payload}")

    username_from_payload: str = payload.get("sub")
    if username_from_payload is None:
        print(f"'sub' (username) not found in token payload.")
        print(f"-------------------------")
        return None
    print(f"Username from token payload: {username_from_payload}")

    user_in_db_obj = await get_user(username=username_from_payload)
    if user_in_db_obj is None:
        print(f"User '{username_from_payload}' (from token) not found in database.")
        print(f"-------------------------")
        return None
    
    print(f"Successfully authenticated user from cookie: {user_in_db_obj.username}")
    print(f"-------------------------")
    return User(username=user_in_db_obj.username)


async def get_current_user_or_redirect(request: Request) -> User:
    print(f"--- Auth Check for: {request.url} (Effective scheme via x-forwarded-proto: {request.headers.get('x-forwarded-proto', request.url.scheme)}) ---")
    user = await get_current_user_from_cookie(request)
    
    if user is None:
        print(f"User is None (authentication failed or no cookie), preparing to redirect to login for: {request.url}")
        cfg = get_settings()
        
        if not cfg.moat_base_url:
            # This case should ideally not happen if config is validated properly at startup.
            print("CRITICAL ERROR: moat_base_url is not configured. Cannot form login redirect.")
            raise HTTPException(status_code=500, detail="Authentication service misconfigured: missing base URL.")

        moat_auth_base_str = str(cfg.moat_base_url).rstrip('/')
        
        login_path_segment = "moat/auth/login"

        if not moat_auth_base_str.endswith('/'):
            moat_auth_base_str += '/'
        
        base_login_url = urljoin(moat_auth_base_str, login_path_segment)
        original_url_str = str(request.url)
        final_redirect_uri_for_login = original_url_str
        current_effective_scheme = request.headers.get("x-forwarded-proto", request.url.scheme)

        if current_effective_scheme == "https" and original_url_str.startswith("http://"):
            final_redirect_uri_for_login = original_url_str.replace("http://", "https://", 1)
            print(f"DEBUG: Upgraded redirect_uri for login form from '{original_url_str}' to '{final_redirect_uri_for_login}' due to effective scheme being HTTPS.")
        
        login_url_with_redirect = f"{base_login_url}?redirect_uri={quote_plus(final_redirect_uri_for_login)}"
        
        print(f"Redirecting unauthenticated user to: {login_url_with_redirect}")
        
        headers = {"Location": login_url_with_redirect}
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
