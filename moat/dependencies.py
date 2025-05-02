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
        print(f"No access token cookie found for {request.url}")
        return None

    payload = decode_access_token(token)
    if payload is None:
        print(f"Invalid or expired access token found in cookie for {request.url}")
        return None
    
    username = payload.get("sub")
    if not username:
        print(f"No username found in access token for {request.url}")
        return None

    return User(username=username)

async def get_current_user_or_redirect(request: Request) -> User:
    """
    Dependency that retrieves the current user from the access token cookie.
    If the user is not authenticated, it redirects to the login page.
    """
    cfg = get_settings()
    user = await get_current_user_from_cookie(request)

    if user is None:
        print(f"No valid user found for {request.url}, redirecting to login.")
        # Determine redirect target based on moat_base_url
        login_redirect_target = cfg.moat_base_url if cfg.moat_base_url else "/"
        
        headers = {"Location": f"/moat/auth/login?next={quote_plus(str(request.url))}"}
        
        #Construct delete cookie header - force browser to forget the invalid cookie
        delet