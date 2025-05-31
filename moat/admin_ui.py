from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import yaml
import asyncio

from moat.models import User
from moat.dependencies import get_current_user_or_redirect
from moat.config import get_settings, save_settings, CONFIG_FILE_PATH, load_config
from moat.runtime_config import apply_settings_changes_to_runtime

router = APIRouter(prefix="/moat/admin", tags=["admin_ui"])
templates = Jinja2Templates(directory="moat/templates")

@router.get("/config", response_class=HTMLResponse)
async def view_config_form(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    success: bool = False,
    error_message: str = ""
):
    """Displays the Moat configuration form."""
    try:
        config_content = yaml.dump(load_config().model_dump(), indent=2)
    except Exception as e:
        config_content = f"Error loading config: {e}"
        error_message = f"Error loading config from file: {e}"  # More specific error
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
    """Updates the Moat configuration from the submitted form data."""
    try:
        # Attempt to load the YAML data
        cfg_dict = yaml.safe_load(config_content)

        # Validate the loaded data against the MoatSettings model
        cfg = MoatSettings(**cfg_dict)

        # Save the validated settings
        if save_settings(cfg):
            # Successfully saved, now apply runtime changes
            await apply_settings_changes_to_runtime(None, cfg)

            # Redirect back to the config page with a success message.
            redirect_url = request.url_for("view_config_form")
            success_query_params = {"success": "true"}
            redirect_url = str(request.url.include_query_params(**success_query_params))
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