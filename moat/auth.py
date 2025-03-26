from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from typing import Optional
from urllib.parse import quote_plus, unquote_plus, urljoin, urlparse

from pydantic import HttpUrl

from .models import User
from .security import create_access_token, verify_password
from .database import get_user
from .dependencies import ACCESS_TOKEN_COOKIE_NAME, get_current_user_from_cookie
from .config import get_settings

router = APIRouter(prefix="/moat/auth", tags=["authentication"])
templates = Jinja2Templates(directory="moat/templates")

async def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Authenticates a user against the database.
    """
    user = await get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return User(username=user.username)

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: str = None):
    """
    Display the login form.
    """
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Process the login form and set the access token cookie.
    """
    user = await authenticate_user(username, password)
    if not user:
        #Potentially add delay to mitigate brute-force attacks
        login_url = request.url_for("login_form").include_query_params(error="Invalid username or password")
        return RedirectResponse(url=str(login_url), status_code=status.HTTP_303_SEE_OTHER)

    # Create access token
    access_token = create_access_token(data={"sub": user.username})

    # Set the access token as a cookie
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    cfg = get_settings()
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection_for_cookie = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )

    print(f"POST /login - Setting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie}")
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure_connection_for_cookie,
        samesite="Lax",
        domain=cookie_domain_setting,
        path="/"
    )

    return response

@router.get("/logout")
async def logout(request: Request):
    """
    Clear the access token cookie and redirect to the home page.  If `logout_redirect` is set as a query parameter,
    redirect there *instead* of home, but only if it's a safe redirect.

    Logout redirect must be a full URL, and must share a root domain with the Moat instance (to prevent open redirect vulnerabilities).
    """
    cfg = get_settings()
    logout_redirect_target_url = "/"
    logout_redirect_param = request.query_params.get("logout_redirect")
    
    if logout_redirect_param:
        try:
            # Pydantic's HttpUrl validator will raise an exception for invalid URLs.
            redirect_url = HttpUrl(logout_redirect_param)

            # Check if the redirect URL shares a root domain with the Moat instance.
            moat_url = urlparse(str(cfg.moat_base_url))
            redirect_url_parsed = urlparse(str(redirect_url))

            if moat_url.netloc == redirect_url_parsed.netloc or "localhost" in moat_url.netloc or "127.0.0.1" in moat_url.netloc:
                # Either exact match, or we're running on localhost (allow any localhost redirect for dev).
                logout_redirect_target_url = str(redirect_url) # Validated HttpUrl converted back to string
            else:
                print(f"GET /logout - Redirect to '{logout_redirect_param}' blocked: different root domain.")
        except ValueError:
            print(f"GET /logout - Invalid logout_redirect URL: '{logout_redirect_param}'.")
    
    print(f"GET /logout - Redirecting to: {logout_redirect_target_url} after logout.")

    response = RedirectResponse(url=logout_redirect_target_url, status_code=status.HTTP_303_SEE_OTHER)
    
    cookie_domain_setting = cfg.cookie_domain
    is_secure_connection_for_cookie_delete = (
        request.url.scheme == "https" or
        request.headers.get("x-forwarded-proto") == "https"
    )
    print(f"GET /logout - Deleting cookie. Domain: '{cookie_domain_setting}', Secure: {is_secure_connection_for_cookie_delete}")

    response.delete_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        path="/",
        domain=cookie_domain_setting,
        secure=is_secure_connection_for_cookie_delete,
        httponly=True,
        samesite="Lax"
    )
    return response