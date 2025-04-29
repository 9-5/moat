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
    config_content = yaml.dump(load_config().model_dump(), indent=2, sort_keys=False) # Removed get_current_config_as_dict
    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "error_message": error_message,
        "success": success,
        "health_status": await get_health_status()
    })

def construct_redirect_url_with_query_params(url: str, params: dict):
    from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
    url_parts = list(urlparse(url))
    query = dict(parse_qs(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)

@router.post("/config", response_class=HTMLResponse)
async def handle_config_form(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    config_content: str = Form(...)
):
    """Handles the submission of the configuration form."""
    try:
        # Load and validate the configuration from the form
        new_config_dict = yaml.safe_load(config_content)
        validated_settings = MoatSettings(**new_config_dict)

        # Save the new configuration
        if await save_settings(validated_settings):
            # Apply settings changes to the runtime environment
            cfg = get_settings() # Get current settings
            await apply_settings_changes_to_runtime(cfg, validated_settings)

            # Redirect back to the config page with a success message
            redirect_url = request.url_for("view_config_form") # Use the route name
            redirect_url = construct_redirect_url_with_query_params(success=True, url=str(redirect_url))
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
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
        "success": False,
        "health_status": await get_health_status()
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