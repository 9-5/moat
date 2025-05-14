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
    """Updates the configuration based on the submitted form data."""
    try:
        # Validate the YAML format
        config_data = yaml.safe_load(config_content)

        # Save the new configuration
        if save_settings(config_data):
            # Apply the new settings to the running application
            cfg = get_settings()
            old_settings = None #TODO: Retrive old settings for comparison?
            await apply_settings_changes_to_runtime(old_settings, cfg)

            # Redirect with a success message
            redirect_url = request.url_for("view_config_form")
            redirect_url = _construct_url_with_query_params(success=True, base_url=redirect_url)
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
    success: bool = False,
    error_message: Optional[str] = None
):
    """Displays the list of static services."""
    settings = get_settings()
    return templates.TemplateResponse("admin_services.html", {
        "request": request,
        "current_user": current_user,
        "static_services": settings.static_services,
        "success": success,
        "error_message": error_message
    })

@router.post("/services/add", response_class=HTMLResponse)
async def add_service(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    hostname: str = Form(...),
    target_url: HttpUrl = Form(...)
):
    """Adds a new static service."""
    try:
        config_dict = get_current_config_as_dict()
        if "static_services" not in config_dict or config_dict["static_services"] is None:
            config_dict["static_services"] = []

        new_service = {"hostname": hostname, "target_url": str(target_url)}  # Convert HttpUrl to str

        config_dict["static_services"].append(new_service)
        if save_settings(config_dict):
            cfg = get_settings()
            old_settings = None #TODO: Retrive old settings for comparison?
            await apply_settings_changes_to_runtime(old_settings, cfg)

            redirect_url = request.url_for("view_services")
            redirect_url = _construct_url_with_query_params(success=True, base_url=redirect_url)

            return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
        else:
            error_message = "Failed to save new service. Check server logs for details."
    except ValueError as ve:
         error_message = f"Validation error: {ve}"
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
    
    redirect_url = request.url_for("view_services")
    redirect_url = _construct_url_with_query_params(error_message=error_message, base_url=redirect_url)
    return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)

@router.post("/services/delete/{hostname}", response_class=HTMLResponse)
async def delete_service(
    request: Request,
    hostname: str,
    current_user: User = Depends(get_current_user_or_redirect)
):
    """Deletes a static service."""
    try:
        config_dict = get_current_config_as_dict()
        if "static_services" in config_dict and config_dict["static_services"] is not None:
            config_dict["static_services"] = [
                service for service in config_dict["static_services"] if service["hostname"] != hostname
            ]
            if save_settings(config_dict):
                cfg = get_settings()
                old_settings = None #TODO: Retrive old settings for comparison?
                await apply_settings_changes_to_runtime(old_settings, cfg)

                redirect_url = request.url_for("view_services")
                redirect_url = _construct_url_with_query_params(success=True, base_url=redirect_url)
                return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
            else:
                error_message = "Failed to delete service. Check server logs for details."
        else:
            error_message = f"Service with hostname '{hostname}' not found."
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"

    redirect_url = request.url_for("view_services")
    redirect_url = _construct_url_with_query_params(error_message=error_message, base_url=redirect_url)
    return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/services/edit/{hostname}", response_class=HTMLResponse)
async def view_edit_service(
    request: Request,
    hostname: str,
    current_user: User = Depends(get_current_user_or_redirect),
    error_message: Optional[str] = None
):
    """Displays the edit form for a specific static service."""
    settings = get_settings()
    service = next((s for s in settings.static_services if s.hostname == hostname), None)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service with hostname '{hostname}' not found")
    return templates.TemplateResponse("admin_edit_service.html", {
        "request": request,
        "current_user": current_user,
        "hostname": hostname,
        "target_url": service.target_url,
        "error_message": error_message
    })

@router.post("/services/edit/{hostname}", response_class=HTMLResponse)
async def update_service(
    request: Request,
    hostname: str,
    current_user: User = Depends(get_current_user_or_redirect),
    target_url: HttpUrl = Form(...)
):
    """Updates an existing static service."""
    try:
        config_dict = get_current_config_as_dict()
        if "static_services" in config_dict and config_dict["static_services"] is not None:
            for service in config_dict["static_services"]:
                if service["hostname"] == hostname:
                    service["target_url"] = str(target_url)  # Update the target URL
                    break
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service with hostname '{hostname}' not found")

            if save_settings(config_dict):
                cfg = get_settings()
                old_settings = None #TODO: Retrive old settings for comparison?
                await apply_settings_changes_to_runtime(old_settings, cfg)

                redirect_url = request.url_for("view_services")
                redirect_url = _construct_url_with_query_params(success=True, base_url=redirect_url)
                return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
            else:
                error_message = "Failed to update service. Check server logs for details."
        else:
            error_message = f"Service with hostname '{hostname}' not found."

    except ValueError as ve:
        error_message = f"Validation error: {ve}"
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"

    redirect_url = request.url_for("view_edit_service", hostname=hostname)
    redirect_url = _construct_url_with_query_params(error_message=error_message, base_url=redirect_url)
    return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)

def _construct_url_with_query_params(base_url: str = "", params: dict = {}, success: bool = False, error_message: Optional[str] = None) -> str:
    """Constructs a URL with query parameters."""
    if success:
        params["success"] = "true"
    if error_message:
        params["error_message"] = error_message

    query_string = "&".join([f"{key}={value}" for key, value in params.items()])
    if query_string:
        return f"{base_url}?{query_string}"
    return base_url