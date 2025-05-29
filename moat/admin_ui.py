from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import yaml
import asyncio

from moat.models import User
from moat.dependencies import get_current_user_or_redirect
from moat.config import get_settings, save_settings, CONFIG_FILE_PATH, load_config
from moat.runtime_config import apply_settings_changes_to_runtime
from urllib.parse import urlencode

router = APIRouter(prefix="/moat/admin", tags=["admin_ui"])
templates = Jinja2Templates(directory="moat/templates")

def construct_url_with_query_params(url: str, params: dict) -> str:
    """
    Constructs a URL with added or updated query parameters.
    """
    if params:
        return f"{url}?{urlencode(params)}"
    return url

@router.get("/config", response_class=HTMLResponse)
async def view_config_form(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    success: bool = False,
    error_message: str = ""
):
    """Displays the configuration form in the admin UI."""
    config_content = yaml.dump(load_config().model_dump(), indent=2)
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
    """Handles the submission of the configuration form to update the Moat settings."""
    try:
        # Load the YAML content from the form
        new_config_data = yaml.safe_load(config_content)

        # Validate the new config using the MoatSettings model
        validated_settings = MoatSettings(**new_config_data)

        # Attempt to save the new settings
        if save_settings(validated_settings):
            # If save is successful, reload the configuration and redirect with success message
            redirect_url = request.url_for("view_config_form")
            redirect_url = construct_url_with_query_params(url=str(redirect_url), params={"success": True})
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
        "success": False,
        "error_message": error_message
    })

@router.post("/config/reload", response_class=HTMLResponse)
async def reload_config(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect)
):
    """Reloads the configuration from the config file, applying changes to the running application."""
    try:
        load_config(force_reload=True) # Explicitly reload
        cfg = get_settings()
        await apply_settings_changes_to_runtime(None, cfg)

        # Redirect back to the config page with a success message.
        redirect_url = request.url_for("view_config_form")
        redirect_url = construct_url_with_query_params(success=True, url=str(redirect_url))
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        error_message = f"Failed to reload configuration: {e}"
        return templates.TemplateResponse("admin_config.html", {
            "request": request,
            "current_user": current_user,
            "config_content": yaml.dump(load_config().model_dump(), indent=2),
            "success": False,
            "error_message": error_message
        })