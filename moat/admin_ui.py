from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import yaml
import asyncio

from moat.models import User, StaticServiceConfig
from moat.dependencies import get_current_user_or_redirect
from moat.config import get_settings, save_settings, CONFIG_FILE_PATH, load_config, get_current_config_as_dict
from moat.runtime_config import apply_settings_changes_to_runtime
from moat.service_registry import registry as global_registry

router = APIRouter(prefix="/moat/admin", tags=["admin_ui"])
templates = Jinja2Templates(directory="moat/templates")

def _construct_url_with_query_params(base_url: str, params: dict) -> str:
    """Helper function to construct a URL with query parameters."""
    query_string = "&".join([f"{key}={value}" for key, value in params.items() if value is not None])
    if query_string:
        return f"{base_url}?{query_string}"
    return base_url

@router.get("/config", response_class=HTMLResponse)
async def view_config_form(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    success: bool = False,
    error_message: str = None,
):
    """Displays the configuration form."""
    config_content = yaml.dump(get_current_config_as_dict(), indent=2, sort_keys=False)
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
    config_content: str = Form(...),
):
    """Handles the submission of the configuration form."""
    try:
        # Attempt to load and validate the YAML content
        new_config_data = yaml.safe_load(config_content)
        new_settings = MoatSettings(**new_config_data)

        # Load old settings before saving
        old_settings = get_settings()

        # Save the new settings
        if save_settings(new_settings):
            # Apply runtime config changes
            asyncio.create_task(apply_settings_changes_to_runtime(old_settings, new_settings))

            # Redirect back to the config page with a success message
            redirect_url = request.url.path
            redirect_url = _construct_url_with_query_params(redirect_url, {"success": True})
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
        "error_message": error_message,
        "success": False  # Ensure success is False when there's an error
    })


@router.get("/health", response_class=HTMLResponse)
async def view_health(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect)
):
    """Displays the system health status."""
    health_status = await get_health_status()
    return templates.TemplateResponse("admin_health.html", {
        "request": request,
        "current_user": current_user,
        "health_status": health_status
    })

@router.get("/services", response_class=HTMLResponse)
async def view_services(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    success: bool = False,
    error_message: str = None,
):
    """Displays the registered services and allows management."""
    services = await global_registry.get_all_services()
    return templates.TemplateResponse("admin_services.html", {
        "request": request,
        "current_user": current_user,
        "services": services,
        "health_status": await get_health_status(),
        "success": success,
        "error_message": error_message
    })

@router.post("/services/delete/{hostname}", response_class=HTMLResponse)
async def delete_service(
    request: Request,
    hostname: str,
    current_user: User = Depends(get_current_user_or_redirect),
):
    """Deletes a service from the registry."""
    try:
        await global_registry.remove_service(hostname)
        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(redirect_url, {"success": True})
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