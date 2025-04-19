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


async def process_container_labels(container, action: str):
    """
    Extracts labels from a container and registers/unregisters it as a service.
    """
    cfg = get_settings()
    label_prefix = cfg.moat_label_prefix
    enable_label = f"{label_prefix}.enable"
    hostname_label = f"{label_prefix}.hostname"
    port_label = f"{label_prefix}.port"
    target_label =  f"{label_prefix}.target"

    if enable_label in container.labels:
        try:
            enable = str(container.labels.get(enable_label)).lower() == "true"
            hostname = container.labels.get(hostname_label)
            port = container.labels.get(port_label)
            target = container.labels.get(target_label)

            if enable and hostname and port:
                target_url = f"http://{container.name}:{port}"
                if target:
                     target_url = target

                if action == "start":
                    print(f"Docker Monitor: Registering {hostname} -> {target_url} from container {container.name} ({container.short_id})")
                    await global_registry.register_service(hostname, target_url)
                elif action == "die":
                    print(f"Docker Monitor: Unregistering {hostname} from container {container.name} ({container.short