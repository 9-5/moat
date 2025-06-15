import asyncio
from typing import Optional

from .config import MoatSettings
from .service_registry import registry as global_registry
from .docker_monitor import watch_docker_events, stop_docker_monitor_task, is_docker_monitor_running

_runtime_docker_monitor_task: Optional[asyncio.Task] = None

async def apply_settings_changes_to_runtime(
    old_settings: Optional[MoatSettings],
    new_settings: MoatSettings,
    loop: Optional[asyncio.AbstractEventLoop] = None
):
    """Applies changes between old and new settings to the running application's state."""
    global _runtime_docker_monitor_task
    print("RuntimeConfig: Applying settings changes...")

    current_services_in_registry = await global_registry.get_all_services()
    
    old_static_hostnames = set()
    if old_settings and old_settings.static_services:
        old_static_hostnames = {s.hostname for s in old_settings.static_services}
    
    new_static_services_map = {}
    if new_settings.static_services:
        new_static_services_map = {s.hostname: str(s.target_url).rstrip('/') for s in new_settings.static_services}

    for hostname, (_, source_type, _) in current_services_in_registry.items():
        if source_type == "static" and hostname not in new_static_services_map:
            print(f"RuntimeConfig: Removing static service '{hostname}' no longer in config.")
            await global_registry.remove_service(hostname)

    if new_settings.static_services:
        for service_conf in new_settings.static_services:
            target_url = str(service_conf.target_url).rstrip('/')
            current_target, current_source, _ = current_services_in_registry.get(service_conf.hostname, (None, None, None))
            if current_source == "static" and current_target == target_url:
                continue
            print(f"RuntimeConfig: Adding/Updating static service '{service_conf.hostname}' -> '{target_url}'")
            await global_registry.add_service(
                service_conf.hostname,
                target_url,
                source_type="static"
            )

    docker_settings_changed = False
    if old_settings:
        if (old_settings.docker_monitor_enabled != new_settings.docker_monitor_enabled or
            old_settings.moat_label_prefix != new_settings.moat_label_prefix):
            docker_settings_changed = True
    else:
        docker_settings_changed = new_settings.docker_monitor_enabled

    if docker_settings_changed or (new_settings.docker_monitor_enabled and not await is_docker_monitor_running()):
        print(f"RuntimeConfig: Docker monitor settings changed or needs starting.")
        if await is_docker_monitor_running():
            print("RuntimeConfig: Stopping existing Docker monitor...")
            await stop_docker_monitor_task() # This signals the task in docker_monitor.py
            if _runtime_docker_monitor_task and not _runtime_docker_monitor_task.done():
                 try:
                    await asyncio.wait_for(_runtime_docker_monitor_task, timeout=5.0)
                 except asyncio.TimeoutError:
                    print("RuntimeConfig: Timeout waiting for old Docker monitor task to stop.")
                 except Exception as e:
                    print(f"RuntimeConfig: Error ensuring old Docker monitor task stopped: {e}")
            _runtime_docker_monitor_task = None

        if new_settings.docker_monitor_enabled:
            print("RuntimeConfig: Starting Docker monitor...")
            current_loop = loop or asyncio.get_event_loop()
            _runtime_docker_monitor_task = current_loop.create_task(watch_docker_events())
        else:
            print("RuntimeConfig: Docker monitoring is disabled in new configuration.")
    
    print("RuntimeConfig: Settings changes applied.")

async def get_runtime_docker_monitor_task() -> Optional[asyncio.Task]:
    """Returns the current docker monitor task instance managed by this module."""
    global _runtime_docker_monitor_task
    return _runtime_docker_monitor_task

async def set_runtime_docker_monitor_task(task: Optional[asyncio.Task]):
    """Sets the docker monitor task instance, typically used by server startup/shutdown."""
    global _runtime_docker_monitor_task
    _runtime_docker_monitor_task = task
