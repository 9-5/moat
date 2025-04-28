from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import asyncio
from watchdog.observers import Observer # type: ignore
from watchdog.events import FileSystemEventHandler # type: ignore
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, quote_plus, urljoin

from .auth import router as auth_router
from .proxy import reverse_proxy
from .dependencies import get_current_user_or_redirect, User, get_current_user_from_cookie # Added get_current_user_from_cookie
from .database import init_db
from .docker_monitor import stop_docker_monitor_task, is_docker_monitor_running # For health check & shutdown
from .config import get_se
... (FILE CONTENT TRUNCATED) ...
ing" if docker_running else "not_running"
    
    effective_docker_status = "unknown"
    if cfg.docker_monitor_enabled:
        effective_docker_status = "enabled_and_running" if docker_running else "enabled_not_running"
    else:
        effective_docker_status = "disabled"

    return {
        "status": "ok",
        "docker_monitor_configured": docker_configured_status,
        "docker_monitor_active": docker_runtime_status,
        "effective_docker_status": effective_docker_status
    }

@app.get("/moat/protected-test", tags=["system"])
async def protected_test_route(current_user: User = Depends(get_current_user_or_redirect)):
    return {"message": f"Hello {current_user.username}, you have access to this protected Moat endpoint!"}

@app.get("/moat", tags=["system"])
async def moat_home(request: Request, current_user: Optional[User] = Depends(get_current_user_from_cookie)):
    """Simple home page that either redirects to the admin config or shows a basic welcome."""
    if current_user:
        return RedirectResponse("/moat/admin/config", status_code=302)
    else:
        return {"message": "Welcome to Moat! Please log in to configure."}