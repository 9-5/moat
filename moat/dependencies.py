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
        print(f"No {ACCESS_TOKEN_COOKIE_NAME} cookie found for {request.url}, user is not authenticated.")
        return None

    payload = decode_access_token(token)
    if not payload:
        print(f"Invalid or expired token found in {ACCESS_TOKEN_COOKIE_NAME} cookie for {request.url}")
        return None

    username = payload.get("sub")
    if not username:
        print(f"Invalid payload in {ACCESS_TOKEN_COOKIE_NAME} cookie, 'sub' claim missing for {request.url}")
        return None

    user_from_db = await get_user(username)  # Await the coroutine
    if not user_from_db:
        print(f"User '{username}' from {ACCESS_TOKEN_COOKIE_NAME} cookie not found in database for {request.url}")
        return None

    user = User(username=user_from_db.username)
    print(f"User '{user.username}' found based on {ACCESS_TOKEN_COOKIE_NAME} cookie for {request.url}")
    return user

async def get_current_user_or_redirect(request: Request) -> User:
    user = await get_current_user_from_cookie(request)
    if not user:
        cfg = get_settings()
        login_url = request.url_for("login_form")

        #if cfg.moat_base_url:
        #    # Ensure the login URL is absolute, pointing to Moat's login page
        #    login_url = urljoin(str(cfg.moat_base_url), login_url)  # type: ignore # cfg.moat_base_url is a HttpUrl

        # Construct the 'next' URL, which is the URL the user was trying to access.
        # This URL is encoded and passed to the login page so that the user can be redirected back after login.
        next_url = quote_plus(str(request.url))
        full_login_url = f"{login_url}?next={next_url}"

        print(f"No active session found for {request.url}, redirecting to login: {full_login_url}")

        headers = {"Location": full_login_url} # Set the Location header for redirection

        # Manually construct the 307 Temporary Redirect response
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