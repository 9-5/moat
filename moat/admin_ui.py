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
    config_content = yaml.dump(load_config().model_dump(), indent=2, sort_keys=False)

    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "current_user": current_user,
        "config_content": config_content,
        "error_message": error_message,
        "success": success
    })

def add_success_parameter_to_query_params(url: str, success: bool) -> str:
    """Adds or updates the 'success' parameter in a URL's query string."""
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    query_params['success'] = [str(success).lower()]  # Ensure boolean is lowercase string

    encoded_query_string = urlencode(query_params, doseq=True) # doseq handles lists properly
    
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        encoded_query_string,
        parsed_url.fragment
    ))
    return new_url

@router.post("/config", response_class=HTMLResponse)
async def update_config(
    request: Request,
    current_user: User = Depends(get_current_user_or_redirect),
    config_content: str = Form(...)
):
    error_message = ""
    try:
        # Attempt to parse the YAML content
        new_config_data = yaml.safe_load(config_content)

        # Validate the new configuration using the MoatSettings model
        validated_settings = MoatSettings(**new_config_data)

        # Save the new configuration to the file
        if await save_settings(validated_settings):
            # Construct a redirect URL, preserving existing query parameters and adding success=true
            redirect_url = request.url
            redirect_url = add_success_parameter_to_query_params(str(redirect_url), success=True)
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