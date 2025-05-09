from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import yaml
import asyncio

from moat.models import User 
from moat.dependencies import get_current_user_or_redirect
from moat.config import get_settings, save_settings, CONFIG_FILE_PATH, load_config
from moat.runtime_config import apply_settings_changes_to_runtime
from moat.database import create_user_db

router = APIRouter(prefix="/moat/admin", tags=["admin_ui"])
templates = Jinja2Templates(directory="moat/templates")

@router.get("/config", response_class=HTMLResponse)
async def view_config_form(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    success: bool = False,
    error_message: str = ""
):
    """Displays the configuration form."""
    config_content = ""
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config_content = f.read()
    except FileNotFoundError:
        error_message = "Configuration file not found."
    
    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "success": success,
        "error_message": error_message,
    })

@router.post("/config", response_class=HTMLResponse)
async def update_config(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    config_content: str = Form(...)
):
    """Updates the configuration file."""
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write(config_content)

        # Reload config and apply runtime settings
        load_config(force_reload=True)
        
        success_message = "Configuration updated successfully."
        redirect_url = request.url_for("view_config_form")
        redirect_url = _construct_url_with_query_params(success=True)
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
        
    except yaml.YAMLError as ye:
        error_message = f"Invalid YAML format: {ye}"
    except ValueError as ve: 
        error_message = f"Configuration validation error: {ve}"
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"

    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content, 
        "error_message": error_message
    })

@router.get("/users", response_class=HTMLResponse)
async def view_users(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    error_message: str = ""
):
    """Displays the users list."""
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "current_user": current_user,
        "error_message": error_message
    })

@router.get("/users/create", response_class=HTMLResponse)
async def view_create_user(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    error_message: str = ""
):
    """Displays the create user form."""
    return templates.TemplateResponse("admin_create_user.html", {
        "request": request,
        "current_user": current_user,
        "error_message": error_message
    })

@router.post("/users/create", response_class=HTMLResponse)
async def create_user(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    username: str = Form(...),
    password: str = Form(...)
):
    """Creates a new user."""
    try:
        user = User(username=username)
        await create_user_db(user, password)
        redirect_url = request.url_for("view_users")
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as ve:
        error_message = f"User creation error: {ve}"
        return templates.TemplateResponse("admin_create_user.html", {
            "request": request,
            "current_user": current_user,
            "error_message": error_message
        })

@router.get("/services", response_class=HTMLResponse)
async def view_services(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    error_message: str = ""
):
    """Displays the services list."""
    services = await global_registry.get_all_services()
    return templates.TemplateResponse("admin_services.html", {
        "request": request,
        "current_user": current_user,
        "services": services,
        "error_message": error_message
    })

@router.post("/services/delete/{hostname}", response_class=HTMLResponse)
async def delete_service(
    request: Request,
    hostname: str,
    current_user: User = Depends(get_current_user_or_redirect)
):
    """Deletes a service by hostname."""
    try:
        await global_registry.remove_service_by_hostname(hostname)
        redirect_url = request.url_for("view_services")
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except KeyError:
        error_message = f"Service with hostname '{hostname}' not found."
        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(redirect_url, {"error_message": error_message})
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(redirect_url, {"error_message": error_message})
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)

def _construct_url_with_query_params(base_url: str, params: dict) -> str:
    """Constructs a URL with query parameters."""
    query_string = "&".join([f"{key}={value}" for key, value in params.items()])
    if query_string:
        return f"{base_url}?{query_string}"
    return base_url