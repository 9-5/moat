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
        print("No token found in cookie.")
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        print("Token is invalid.")
        return None
    username: str = payload.get("sub")
    if username is None:
        print("Token has no subject.")
        return None
    user = User(username=username)
    print(f"Decoded username from token: {user.username}")
    return user

async def get_current_user_or_redirect(request: Request) -> User:
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)
    if user is None:
        print("No current user, redirecting to login.")
        #Construct the login URL, preserving the original path in 'next'
        next_url = quote_plus(str(request.url))
        login_url = f"/moat/auth/login?next={next_url}"
        
        headers = {"Location": login_url}

        # Manually construct the "Set-Cookie" header to delete the cookie,
        # including