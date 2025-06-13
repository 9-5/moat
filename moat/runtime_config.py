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
    
    old
... (FILE CONTENT TRUNCATED) ...

get_event_loop()
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