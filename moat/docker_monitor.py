import asyncio
import docker # type: ignore
from docker.errors import NotFound # type: ignore

from .service_registry import registry as global_registry
from .config import get_settings

_monitor_task_should_stop = asyncio.Event()
_monitor_task_active = False

async def stop_docker_monitor_task():
    global _monitor_task_should_stop, _monitor_task_active
    if _monitor_task_active:
        print("Docker Monitor: Stop signal received.")
        _monitor_task_should_stop.set()
    else:
        print("Docker Monitor: Stop signal received, but monitor was not marked active.")

async def is_docker_monitor_running() -> bool:
    global _monitor_task_active
    return _monitor_task_active

async def process_container_labels(container, action: s
... (FILE CONTENT TRUNCATED) ...
d"])
                        await process_container_labels(container, action)
                    except NotFound:
                        if action == "start":
                            # Retry by Name as the container might only be resolvable by name after start
                            try:
                                container = client.containers.get(event["id"])
                                await process_container_labels(container, action)
                            except NotFound:
                                print(f"Docker Monitor: Container {event['id'][:12]} not found for event {action}, skipping.")
                        elif action == "die":
                            await global_registry.unregister_service_b