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

    username = payload.get("sub")
    if not username:
        print("No username found in access token.")
        return None

    user = await get_user(username)
    if user is None:
        print(f"User '{username}' from access token not found in database.")
        return None

    print(f"User '{username}' authenticated from cookie.")
    return User(username=user.username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Retrieves the current user from the access token cookie. If no valid token 
    is found, redirects the user to the login page, preserving the originally 
    requested URL for redirection after successful login.
    """
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)
    if user is None:
        print(f"No valid user found, redirecting to login: {request.url}")
        
        # URL-encode the original path so that the login page can redirect back
        login_redirect_url_encoded = quote_plus(str(request.url))
        
        # Construct the full login URL with the 'next' parameter
        login_url = f"/moat/auth/login?next={login_redirect_url_encoded}"

        headers = {"Location": login_url