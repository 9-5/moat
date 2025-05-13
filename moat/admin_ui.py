from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import yaml
import asyncio

from moat.models import User, StaticServiceConfig
from moat.dependencies import get_current_user_or_redirect
from moat.config import get_settings, save_settings, CONFIG_FILE_PATH, load_config, get_current_config_as_dict
from moat.runtime_config import apply_settings_changes_to_runtime
from typing import List, Optional
from pydantic import HttpUrl

router = APIRouter(prefix="/moat/admin", tags=["admin_ui"])
templates = Jinja2Templates(directory="moat/templates")

@router.get("/config", response_class=HTMLResponse)
async def view_config_form(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    success: bool = False,
    error_message: Optional[str] = None
):
    """Displays the configuration form."""
    config_content = yaml.dump(get_current_config_as_dict(), indent=2, sort_keys=False) # Load config for display

    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "success": success,
        "error_message": error_message
    })


@router.post("/config", response_class=HTMLResponse)
async def update_config(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    config_content: str = Form(...)
):
    """Updates the configuration and redirects to the config view with a success or error message."""
    try:
        # Attempt to save the configuration
        if save_settings(config_content):
            # If save is successful, apply settings changes and redirect with success message
            new_settings = load_config()  # Reload to ensure we have the latest validated settings
            await apply_settings_changes_to_runtime(None, new_settings)

            redirect_url = request.url_for("view_config_form")
            redirect_url = _construct_url_with_query_params(redirect_url, {"success": "true"})
            return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
        else:
            error_message = "Failed to save configuration. Check server logs for details. Validation might have failed."

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

@router.get("/services", response_class=HTMLResponse)
async def view_services(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    error_message: Optional[str] = None,
    success: bool = False
):
    """Displays the list of registered services."""
    services = await asyncio.gather(*[
        global_registry.get_service_by_hostname(hostname)
        for hostname in await global_registry.get_all_hostnames()
    ])

    return templates.TemplateResponse("admin_services.html", {
        "request": request,
        "current_user": current_user,
        "services": services,
        "error_message": error_message,
        "success": success
    })

@router.post("/services/remove/{hostname}", response_class=HTMLResponse)
async def remove_service(
    request: Request,
    hostname: str,
    current_user: User = Depends(get_current_user_or_redirect)
):
    """Removes a service by hostname."""
    try:
        await global_registry.remove_service_by_hostname(hostname)
        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(success=True, base_url=redirect_url)

        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(redirect_url, {"error_message": error_message})
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)

@router.post("/services/refresh", response_class=HTMLResponse)
async def refresh_services(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect)
):
    """Refreshes services from Docker (if enabled) and static config."""
    try:
        # Reload settings to ensure we have the most up-to-date config.
        new_settings = load_config()
        await apply_settings_changes_to_runtime(None, new_settings) # 'None' for old_settings means "apply all".

        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(success=True, base_url=redirect_url)
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(redirect_url, {"error_message": error_message})
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)

@router.post("/services/add", response_class=HTMLResponse)
async def add_static_service(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    hostname: str = Form(...),
    target_url: HttpUrl = Form(...)
):
    """Adds a static service to the configuration."""
    try:
        cfg = load_config()
        new_service = StaticServiceConfig(hostname=hostname, target_url=target_url)
        cfg_dict = get_current_config_as_dict()

        # Ensure static_services exists and is a list
        if 'static_services' not in cfg_dict or not isinstance(cfg_dict['static_services'], list):
            cfg_dict['static_services'] = []

        cfg_dict['static_services'].append(new_service.model_dump()) # Append pydantic model as a dict
        save_settings(yaml.dump(cfg_dict, sort_keys=False)) # Save the updated config to file

        # Reload config and apply changes to runtime
        new_settings = load_config()
        await apply_settings_changes_to_runtime(None, new_settings)

        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(success=True)
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