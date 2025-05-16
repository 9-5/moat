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
        print(f"No access token found in cookie.")
        return None

    payload = decode_access_token(token)
    if not payload:
        print(f"Invalid or expired access token in cookie.")
        return None

    username = payload.get("sub")
    if not username:
        print(f"No username found in access token payload.")
        return None

    return User(username=username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Tries to get the current user from the access token cookie.

    If the user is not authenticated (no valid token), it redirects them to the login page.
    """
    user = await get_current_user_from_cookie(request)

    if not user:
        print(f"User not authenticated, redirecting to login.")
        cfg = get_settings()
        
        # Build the full URL to the login page, including a 'next' parameter