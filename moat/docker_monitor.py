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
    cfg = get_settings() 
    prefix = cfg.moat_label_prefix
    try:
        container_info = docker.from_env().containers.get(container.id)
        labels = container_info.labels
    except NotFound:
        if action in ["stop", "die"]:
            print(f"Docker Monitor: Container {container.id[:12]} not found for {action}, attempting removal by ID.")
            await global_registry.remove_services_by_container_id(container.id)
        return
    except Exception as e:
        print(f"Docker Monitor: Error getting labels for {container.id[:12]}: {e}")
        return

    if labels.get(f"{prefix}.enable") == "true":
        hostname = labels.get(f"{prefix}.hostname")
        port = labels.get(f"{prefix}.port")
        scheme = labels.get(f"{prefix}.scheme", "http")

        if not (hostname and port):
            print(f"Docker Monitor: Missing {prefix}.hostname or {prefix}.port for {container.short_id}")
            return
        
        container_name = container_info.name
        target_url = f"{scheme}://{container_name}:{port}"

        if action in ["start", "unpause"]:
            await global_registry.add_service(hostname, target_url, source_type="docker", container_id=container.id)
        elif action in ["stop", "die", "pause"]:
            await global_registry.remove_service(hostname)


async def initial_scan_containers():
    cfg = get_settings()
    if not cfg.docker_monitor_enabled:
        print("Docker Monitor: Initial scan skipped (disabled).")
        return

    print("Docker Monitor: Performing initial scan of running containers...")
    client = docker.from_env()
    try:
        for container in client.containers.list():
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Initial scan aborted (stop signal).")
                return
            await process_container_labels(container, "start")
    except docker.errors.DockerException as e:
        print(f"Docker Monitor: DockerException during initial scan: {e}. Is Docker running and accessible?")
    except Exception as e:
        print(f"Docker Monitor: Unexpected error during initial scan: {e}")
    print("Docker Monitor: Initial scan complete.")


async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_should_stop.clear()
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")

    try:
        current_cfg = get_settings()
        if not current_cfg.docker_monitor_enabled:
            print("Docker Monitor: Watcher started but immediately disabled by current configuration.")
            _monitor_task_active = False
            return

        await initial_scan_containers()
        if _monitor_task_should_stop.is_set():
            print("Docker Monitor: Watcher stopping after initial scan due to stop signal.")
            _monitor_task_active = False
            return

        print("Docker Monitor: Now watching for Docker events...")
        client = docker.from_env()
        for event in client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Event processing loop received stop signal. Exiting.")
                break

            if event.get("Type") == "container":
                action = event.get("Action")
                if action in ["start", "stop", "die", "pause", "unpause"]:
                    print(f"Docker Monitor: Event - {action} for container {event['id'][:12]}")
                    try:
                        container = client.containers.get(event["id"])
                        await process_container_labels(container, action)
                    except NotFound:
                        if action in ["stop", "die"]:
                            print(f"Docker Monitor: Container {event['id'][:12]} not found after {action} event, attempting removal by ID.")
                            await global_registry.remove_services_by_container_id(event["id"])
                        else:
                            print(f"Docker Monitor: Container {event['id'][:12]} not found for event {action}, skipping.")
                    except Exception as e:
                        print(f"Docker Monitor: Error processing event for {event['id'][:12]}: {e}")
    except docker.errors.DockerException as e:
        print(f"Docker Monitor: DockerException in event stream: {e}. Is Docker running and accessible? Stopping monitor.")
    except Exception as e:
        print(f"Docker Monitor: Error in event stream: {e}. Stopping monitor.")
    finally:
        print("Docker Monitor: Event watcher stopped.")
        _monitor_task_active = False
        _monitor_task_should_stop.clear()