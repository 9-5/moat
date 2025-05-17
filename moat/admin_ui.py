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
    config_content = yaml.dump(load_config().model_dump(exclude_unset=True), indent=2, sort_keys=False)
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
    """Updates the configuration based on the submitted form."""
    try:
        # Validate YAML format
        cfg_dict = yaml.safe_load(config_content)
        if cfg_dict is None:
            cfg_dict = {}

        # Validate against MoatSettings model
        validated_settings = MoatSettings(**cfg_dict)

        # Save the new configuration
        if save_settings(validated_settings):
            # Apply changes to the runtime
            await apply_settings_changes_to_runtime(old_settings=get_settings(), new_settings=validated_settings)

            redirect_url = request.url.path
            redirect_url = _construct_url_with_query_params(success=True)
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