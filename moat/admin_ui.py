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
    error: str = None
):
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            raw_config_content = f.read()
    except FileNotFoundError:
        raw_config_content = "# config.yml not found. Please create one."
        error = error or "config.yml not found."
    except Exception as e:
        raw_config_content = f"# Error loading config.yml: {e}"
        error = error or f"Error loading config.yml: {e}"

    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": raw_config_content,
        "success_message": "Configuration updated successfully and reload attempted!" if success else None,
        "error_message": error
    })

@router.post("/config/save", response_class=HTMLResponse)
async def save_config_from_form(
    request: Request,
    config_content: str = Form(...),
    current_user: User = Depends(get_current_user_or_redirect)
):
    error_message = None
    old_settings_for_apply = None
    try:
        old_settings_for_apply = get_settings() 
        
        new_config_data = yaml.safe_load(config_content)
        if not isinstance(new_config_data, dict):
            raise ValueError("Invalid YAML structure. Root must be a mapping (dictionary).")

        if save_settings(new_config_data): # save_settings also reloads internal _settings in config.py
            reloaded_settings_after_save = get_settings()
            current_loop = asyncio.get_event_loop()
            await apply_settings_changes_to_runtime(old_settings_for_apply, reloaded_settings_after_save, loop=current_loop)
            
            redirect_url = request.url_for("view_config_form").include_query_params(success=True)
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
        "current_user": current__user,
        "config_content": config_content, 
        "error_message": error_message
    })
