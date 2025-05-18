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
    error_message: str = None
):
    """Displays the configuration form."""
    config_content = ""
    try:
        config_content = yaml.dump(load_config().model_dump(), indent=2)
    except Exception as e:
        error_message = f"Failed to load configuration: {e}"

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
    """Handles updating the configuration."""
    error_message = None
    try:
        # Validate YAML format
        yaml.safe_load(config_content)

        # Attempt to save the configuration
        success = save_settings(config_content)

        if success:
            # Redirect with a success message
            redirect_url = request.url_for("view_config_form")
            redirect_url = _construct_url_with_query_params(base_url=str(redirect_url), success=True)
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

def _construct_url_with_query_params(base_url: str = "", params: dict = {}, success: bool = False, error_message: str = None) -> str:
    """Constructs a URL with query parameters."""
    if success:
        params["success"] = "true"
    if error_message:
        params["error_message"] = error_message

    query_string = "&".join([f"{key}={value}" for key, value in params.items()])
    if query_string:
        return f"{base_url}?{query_string}"
    return base_url