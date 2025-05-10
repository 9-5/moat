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
    config_content = yaml.dump(get_current_config_as_dict(), sort_keys=False)
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
    """Handles the submission of the configuration form."""
    try:
        # Validate YAML format
        yaml.safe_load(config_content)

        # Save the configuration
        success = save_settings(config_content)

        if success:
            redirect_url = request.url_for("view_config_form").include_query_params(success=True)
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
        "success": False,
        "error_message": error_message
    })

@router.get("/services", response_class=HTMLResponse)
async def view_services(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    success: bool = False,
    error_message: Optional[str] = None
):
    """Displays the list of services."""
    cfg = get_settings()
    return templates.TemplateResponse("admin_services.html", {
        "request": request,
        "current_user": current_user,
        "static_services": cfg.static_services,
        "success": success,
        "error_message": error_message
    })

@router.post("/services/add", response_class=HTMLResponse)
async def add_service(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    hostname: str = Form(...),
    target_url: str = Form(...)
):
    """Adds a new static service."""
    try:
        # Validate the target URL format
        target_url_httpurl = HttpUrl(target_url)
        
        # Load existing config, add the new service, and save
        cfg_dict = get_current_config_as_dict()
        if 'static_services' not in cfg_dict:
            cfg_dict['static_services'] = []

        new_service = {"hostname": hostname, "target_url": str(target_url_httpurl)}
        cfg_dict['static_services'].append(new_service)

        success = save_settings(cfg_dict)
        if not success:
             raise ValueError("Failed to save configuration. Check server logs for details.")
        redirect_url = request.url_for("view_services").include_query_params(success=True)
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except ValueError as ve:
        error_message = f"Validation error: {ve}"
        redirect_url = request.url_for("view_services").include_query_params(error_message=error_message)
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        redirect_url = request.url_for("view_services").include_query_params(error_message=error_message)
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    
@router.post("/services/delete/{hostname}", response_class=HTMLResponse)
async def delete_service(
    request: Request,
    hostname: str,
    current_user: User = Depends(get_current_user_or_redirect)
):
    """Deletes a static service."""
    try:
        cfg_dict = get_current_config_as_dict()
        if 'static_services' not in cfg_dict:
            error_message = "No static services configured."
            redirect_url = request.url_for("view_services")
            redirect_url = _construct_url_with_query_params(redirect_url, {"error_message": error_message})
            return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)

        static_services = cfg_dict['static_services']
        original_count = len(static_services)
        cfg_dict['static_services'] = [s for s in static_services if s['hostname'] != hostname]
        if len(static_services) == original_count:
             error_message = f"Service with hostname '{hostname}' not found."
             redirect_url = request.url_for("view_services")
             redirect_url = _construct_url_with_query_params(redirect_url, {"error_message": error_message})
             return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)

        success = save_settings(cfg_dict)
        if not success:
            error_message = "Failed to save configuration. Check server logs for details."
            redirect_url = request.url_for("view_services")
            redirect_url = _construct_url_with_query_params(redirect_url, {"error_message": error_message})
            return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
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