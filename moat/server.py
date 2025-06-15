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
from .config import get_settings, load_config, CONFIG_FILE_PATH, MoatSettings
from .admin_ui import router as admin_ui_router
from .runtime_config import apply_settings_changes_to_runtime, get_runtime_docker_monitor_task, set_runtime_docker_monitor_task

app = FastAPI(title="Moat Security Gateway")

# Mount static files
app.mount("/moat/static", StaticFiles(directory="moat/static"), name="static")

# Include authentication routes
app.include_router(auth_router)
app.include_router(admin_ui_router)

# --- Config Hot Reloading Logic ---
_config_observer_instance: Optional[Observer] = None # Store observer instance per app lifecycle

class ConfigFileChangeHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.last_processed_event_time = 0.0 
        self.debounce_period = 1.0 

    def on_modified(self, event):
        if event.is_directory or Path(event.src_path).name != CONFIG_FILE_PATH.name:
            return

        current_time = self.loop.time()
        if current_time - self.last_processed_event_time < self.debounce_period:
            return
        self.last_processed_event_time = current_time

        print(f"Config Watcher: Detected modification in {event.src_path}")
        asyncio.run_coroutine_threadsafe(self.handle_config_reload(), self.loop)

    async def handle_config_reload(self):
        await asyncio.sleep(0.5) 
        try:
            old_settings = get_settings() 
            new_settings = load_config(force_reload=True) 

            print("Config Watcher: Reloading and applying configuration...")
            await apply_settings_changes_to_runtime(old_settings, new_settings, loop=self.loop)
            print("Config Watcher: Configuration reloaded and applied.")
        except FileNotFoundError:
            print("Config Watcher: config.yml deleted? Cannot reload.")
        except Exception as e:
            print(f"Config Watcher: Error during config reload: {e}")


@app.on_event("startup")
async def startup_event():
    global _config_observer_instance
    print("Moat starting up...")
    loop = asyncio.get_event_loop() 

    await init_db()
    print("Database initialized.")

    cfg = get_settings() 
    await apply_settings_changes_to_runtime(None, cfg, loop=loop)

    if _config_observer_instance is None or not _config_observer_instance.is_alive():
        _config_observer_instance = Observer()
        event_handler = ConfigFileChangeHandler(loop=loop)
        config_file_parent_dir = str(CONFIG_FILE_PATH.resolve().parent)
        _config_observer_instance.schedule(event_handler, path=config_file_parent_dir, recursive=False)
        try:
            _config_observer_instance.start()
            print(f"Config Watcher: Started monitoring {CONFIG_FILE_PATH} in {config_file_parent_dir} for changes.")
        except Exception as e:
            print(f"Config Watcher: Failed to start observer: {e}. Hot-reloading of config.yml might not work.")
            if _config_observer_instance and _config_observer_instance.is_alive():
                _config_observer_instance.stop()
                _config_observer_instance.join(timeout=1.0)
            _config_observer_instance = None
    else:
        print("Config Watcher: Observer already alive. Skipping start.")

    print("Moat startup tasks complete.")

@app.on_event("shutdown")
async def shutdown_event():
    global _config_observer_instance
    print("Moat shutting down...")

    if _config_observer_instance and _config_observer_instance.is_alive():
        print("Config Watcher: Stopping observer...")
        _config_observer_instance.stop()
        _config_observer_instance.join(timeout=2.0)
        print("Config Watcher: Observer stopped." if not _config_observer_instance.is_alive() else "Config Watcher: Observer thread did not terminate in time.")
    _config_observer_instance = None

    docker_monitor_task_ref = await get_runtime_docker_monitor_task()
    if docker_monitor_task_ref and not docker_monitor_task_ref.done():
        print("Server Shutdown: Stopping Docker monitor task (via runtime_config)...")
        await stop_docker_monitor_task() # Signal stop
        try:
            await asyncio.wait_for(docker_monitor_task_ref, timeout=5.0)
        except asyncio.TimeoutError:
            print("Server Shutdown: Timeout waiting for Docker monitor task to stop.")
        except Exception as e:
            print(f"Server Shutdown: Error stopping Docker monitor task: {e}")
    await set_runtime_docker_monitor_task(None) 

    print("Moat shutdown complete.")


@app.get("/")
async def handle_moat_root(request: Request):
    cfg = get_settings()
    moat_admin_config_path_segment = "/moat/admin/config" 

    full_admin_config_url = ""
    moat_base_str_for_join = ""

    if cfg.moat_base_url:
        moat_base_str_for_join = str(cfg.moat_base_url).rstrip('/') + '/'
        full_admin_config_url = urljoin(moat_base_str_for_join, moat_admin_config_path_segment.lstrip('/'))
    else:
        # Fallback if moat_base_url is not set (should not happen in a proper setup)
        print("WARNING: moat_base_url not set. Root redirect logic might be unreliable if Moat is proxied complexly.")
        full_admin_config_url = request.url_for("view_config_form") # 'view_config_form' is the name of the admin route function.
                                                                   # This assumes admin_ui router is named. Let's use the path.
        full_admin_config_url = str(request.base_url).rstrip('/') + moat_admin_config_path_segment


    request_host = request.headers.get("host", "").split(":")[0]
    moat_configured_host = ""
    if cfg.moat_base_url:
        parsed_moat_base = urlparse(str(cfg.moat_base_url))
        moat_configured_host = parsed_moat_base.hostname

    print(f"DEBUG: Root path access. Request host: '{request_host}', Moat configured host: '{moat_configured_host}'")

    if request_host and moat_configured_host and request_host == moat_configured_host:
        print(f"DEBUG: Request is for Moat's own root path.")
        current_user = await get_current_user_from_cookie(request) 

        if current_user:
            print(f"DEBUG: User '{current_user.username}' authenticated. Redirecting to admin config: {full_admin_config_url}")
            return RedirectResponse(url=full_admin_config_url)
        else:
            login_path_segment = "moat/auth/login"
            # Use moat_base_str_for_join if available, otherwise construct from request
            base_login_url_base = moat_base_str_for_join if moat_base_str_for_join else str(request.base_url).rstrip('/') + '/'
            base_login_url = urljoin(base_login_url_base, login_path_segment.lstrip('/'))
            
            login_redirect_target = full_admin_config_url
            
            final_login_url = f"{base_login_url}?redirect_uri={quote_plus(login_redirect_target)}"
            print(f"DEBUG: User not authenticated. Redirecting to login for admin access: {final_login_url}")
            return RedirectResponse(url=final_login_url)
    else:
        # Host doesn't match Moat's configured hostname, or moat_base_url is not set up correctly.
        # This means it's a root request for a proxied app OR moat_base_url is missing/misconfigured.
        print(f"DEBUG: Root path request for a different host ('{request_host}') or moat_base_url check failed. Passing to proxy.")
        user_for_proxy = await get_current_user_or_redirect(request) 
        return await reverse_proxy(request)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def catch_all_proxy_route(
    request: Request,
    user_dependency: User = Depends(get_current_user_or_redirect) 
):
    return await reverse_proxy(request) 


@app.get("/moat/health", tags=["system"])
async def health_check():
    cfg = get_settings() 
    docker_running = await is_docker_monitor_running() 
    
    docker_configured_status = "enabled" if cfg.docker_monitor_enabled else "disabled"
    docker_runtime_status = "running" if docker_running else "not_running"
    
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
