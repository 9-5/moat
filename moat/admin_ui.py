from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import yaml
import asyncio

from moat.models import User, StaticServiceConfig
from moat.dependencies import get_current_user_or_redirect
from moat.config import get_settings, save_settings, CONFIG_FILE_PATH, load_config, get_current_config_as_dict
from moat.runtime_config import apply_settings_changes_to_runtime
from typing import List, Optional
from pydantic import HttpUrl

router = APIRouter(prefix="/moat/admin", tags=["admin_ui"])
templates = Jinja2Templates(directory="moat/templates")

@router.get("/config", response_class=HTMLResponse)
async def view_con
... (FILE CONTENT TRUNCATED) ...
ry_params(success=True)
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        redirect_url = request.url_for("view_services")
        redirect_url = _construct_url_with_query_params(redirect_url, {"error_message": error_message})
        return RedirectResponse(url=str(redirect_url), status_code=status.HTTP_303_SEE_OTHER)

def _construct_url_with_query_params(base_url: str, params: dict) -> str:
    """Constructs a URL with query parameters."""
    query_string = "&".join([f"{key}={value}" for key, value in params.items()])
    if query_string:
        return f"{base_url}?{query_string}"
    return base_url