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
    """Displays the configuration form."""
    config_content = ""
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config_content = f.read()
    except FileNotFoundError:
        error_message = f"Configuration file not found: {CONFIG_FILE_PATH}"
    except Exception as e:
        error_message = f"Error reading configuration file: {e}"

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
    """Updates the configuration file."""
    try:
        # Validate the configuration before saving. load_config performs validation.
        validated_settings = None
        try:
             validated_settings = MoatSettings(**yaml.safe_load(config_content))
        except Exception as e:
             raise ValueError(f"Invalid configuration: {e}")
        
        if save_settings(validated_settings):
            # Construct a redirect URL with the success query parameter.
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