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
    Processes the labels of a Docker container and registers/unregisters services
    based on the labels.
    """
    cfg = get_settings()
    labels = container.labels
    prefix = cfg.moat_label_prefix
    enable_label = f"{prefix}.enable"
    hostname_label = f"{prefix}.hostname"
    port_label = f"{prefix}.port"

    if enable_label in labels and labels[enable_label] == "true":
        hostname = labels.get(hostname_label)
        port = labels.get(port_label)
        
        if not hostname or not port:
            print(f"Docker Monitor: Container {container.name} has enable=true but missing hostname or port. Skipping.")
            return

        try:
            port = int(port)
        except ValueError:
            print(f"Docker Monitor: Container {container.name} has invalid port: {port}. Skipping.")
            return

        # Construct the target URL.  This assumes http, but could be extended to support https.
        target_url = f"http://{container.name}:{port}"  # Assumes that Moat is on the same Docker network.
        await global_registry.register_service(hostname, target_url)
        print(f"Docker Monitor: Registered {hostname} -> {target_url} (container: {container.name})")
    else:
        # Clean up if the service was previously enabled but is now disabled.
        # Prevents orphaned routes.
        if hostname_label in labels:
            hostname = labels[hostname_label]
            await global_registry.unregister_service(hostname)
            print(f"Docker Monitor: Unregistered {hostname} (container: {container.name})")


async def watch_docker_events():
    """
    Watches Docker events for container start and stop events to dynamically
    update the service registry.
    """
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")

    try:
        client = docker.from_env()
        async for event in client.events(filters={"type": "container", "event": ["start", "stop", "die", "health_status"]}, decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Stop signal received, exiting event loop.")
                break

            action = event.get("status")
            if action in ["start", "die", "health_status"]: # Health status can also indicate a change in availability
                container_id = event["id"]
                try:
                    container = client.containers.get(container_id)
                    await process_container_labels(container, action)
                except NotFound:
                    # Container might be gone before we process the event.
                    print(f"Docker Monitor: Container {container_id[:12]} not found, skipping.")
                except Exception as e:
                    print(f"Docker Monitor: Error processing container {container_id[:12]}: {e}")
            elif action == "stop":
                # Handle stop events to remove services.
                try:
                    container = client.containers.get(event["id"])
                    if container:
                        await process_container_labels(container, "stop") # Pass "stop" action
                    else:
                        print(f"Docker Monitor: Container {event['id'][:12]} not found for event {action}, skipping.")
                except Exception as e:
                    print(f"Docker Monitor: Error processing event for {event['id'][:12]}: {e}")
            else:
                # Attempt to get container on any event in case it's a restart, etc.
                try:
                    container = client.containers.get(event["id"])
                    if container:
                        await process_container_labels(container, action)
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