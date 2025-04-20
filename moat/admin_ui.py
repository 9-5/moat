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

def create_query_params(success: bool):
    """Helper function to create query parameters for redirects."""
    query_params = {"success": str(success).lower()}
    return "?" + urlencode(query_params)

@router.get("/config", response_class=HTMLResponse)
async def view_config_form(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    success: bool = False,
    error_message: str = None,
):
    """Displays the configuration form."""
    config_content = yaml.dump(load_config().model_dump(), indent=2, sort_keys=False)
    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "error_message": error_message,
        "success": success
    })

@router.post("/config", response_class=HTMLResponse)
async def update_config(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    config_content: str = Form(...),
):
    """Handles the submission of the configuration form."""
    try:
        # Attempt to parse the YAML content
        yaml_data = yaml.safe_load(config_content)

        # Validate the YAML data against the MoatSettings model
        validated_settings = MoatSettings(**yaml_data)

        # Save the validated settings
        if save_settings(validated_settings):
            #If settings are saved correctly, apply them to the runtime.
            await apply_settings_changes_to_runtime(old_settings=get_settings(), new_settings=validated_settings)
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

    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "error_message": error_message,
        "success": False
    })