from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import yaml
import asyncio

from moat.models import User
from moat.dependencies import get_current_user_or_redirect
from moat.config import get_settings, save_settings, CONFIG_FILE_PATH, load_config
from moat.runtime_config import apply_settings_changes_to_runtime
from moat.server import get_health_status
from moat.service_registry import registry as global_registry

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
    config_content = yaml.dump(load_config().model_dump(), sort_keys=False)
    health_status = await get_health_status()
    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "success": success,
        "error_message": error_message,
        "health_status": health_status
    })

@router.post("/config", response_class=HTMLResponse)
async def update_config(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    config_content: str = Form(...)
):
    """Handles the submission of the configuration form."""
    try:
        # Load the YAML content
        cfg_dict = yaml.safe_load(config_content)

        # Validate against the MoatSettings model
        validated_settings = MoatSettings(**cfg_dict)

        # Save the validated settings
        if await save_settings(validated_settings):
            # Optionally, apply the settings changes to the runtime configuration
            await apply_settings_changes_to_runtime(get_settings(), validated_settings)

            # Redirect back to the config page with a success message
            redirect_url = request.url.include_query_params(success=True)
            return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
        else:
            error_message = "Failed to save configuration. Check server logs for details. Validation might have failed."

    except yaml.YAMLError as ye:
        error_message = f"Invalid YAML format: {ye}"
    except ValueError as ve:
        error_message = f"Configuration validation error: {ve}"
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"

    health_status = await get_health_status()
    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "success": False,
        "error_message": error_message,
        "health_status": health_status
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
    current_user: User = Depends(get_current_user_or_redirect)
):
    """Displays the registered services."""
    services = await global_registry.get_all_services()
    return templates.TemplateResponse("admin_services.html", {
        "request": request,
        "current_user": current_user,
        "services": services,
        "health_status": await get_health_status()
    })