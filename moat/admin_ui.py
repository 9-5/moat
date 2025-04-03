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

async def render_admin_config_form(
    request: Request,
    current_user: User,
    config_content: str,
    error_message: str = None,
    success: bool = False
):
    """Helper function to render the admin config form."""
    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "error_message": error_message,
        "success": success
    })


@router.get("/config", response_class=HTMLResponse)
async def view_config_form(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
):
    config_content = yaml.dump(load_config(force_reload=True).model_dump(), sort_keys=False)
    return await render_admin_config_form(request, current_user, config_content)

@router.post("/config", response_class=HTMLResponse)
async def update_config(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    config_content: str = Form(...),
):
    error_message = None
    try:
        # Basic validation
        if not config_content.strip():
            raise ValueError("Configuration cannot be empty.")

        new_config = yaml.safe_load(config_content)
        if not isinstance(new_config, dict):
            raise ValueError("Configuration must be a YAML dictionary.")

        # Load settings and apply changes
        old_settings = get_settings()
        new_settings = MoatSettings(**new_config)  # Pydantic validation

        if save_settings(new_settings):
            await apply_settings_changes_to_runtime(old_settings, new_settings)

            # Redirect to GET /config with a success message. Add query param to indicate success
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

    return await render_admin_config_form(request, current_user, config_content, error_message=error_message, success=False)