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
    Processes the labels of a Docker container to register or unregister it as a service.
    """
    cfg = get_settings()
    labels = container.labels
    label_prefix = cfg.moat_label_prefix
    container_name = container.name
    container_id = container.short_id  # Use short_id for brevity in logs
    
    try:
        enable_label = f"{label_prefix}.enable"
        hostname_label = f"{label_prefix}.hostname"
        target_port_label = f"{label_prefix}.port"

        if enable_label not in labels or hostname_label not in labels or target_port_label not in labels:
            print(f"Docker Monitor: Skipping {container_name} ({container_id}) - missing required labels.")
            return

        if labels[enable_label].lower() != "true":
            print(f"Docker Monitor: Skipping {container_name} ({container_id}) - {enable_label} is not 'true'.")
            return

        hostname = labels[hostname_label]
        try:
            target_port = int(labels[target_port_label])
        except ValueError:
            print(f"Docker Monitor: Invalid port value for {container_name} ({container_id}): {labels[target_port_label]}.")
            return

        # Determine the target URL based on container's network settings
        # This is more robust than assuming a fixed IP
        target_url = None
        try:
            network_settings = container.attrs['NetworkSettings']
            if 'Ports' in network_settings and network_settings['Ports']:
                # Iterate through ports to find the target port
                for internal_port, bindings in network_settings['Ports'].items():
                    if str(target_port) in internal_port: # e.g., "80/tcp"
                        if bindings:
                            # Use the host IP and port if bound
                            target_url = f"http://{bindings[0]['HostIp']}:{bindings[0]['HostPort']}"
                            print(f"Docker Monitor: Container {container_name} ({container_id}) using host binding: {target_url}")
                            break
                        else:
                            # If not bound, assume it's accessible on the container's internal network
                            # and Moat is running in the same network or can access it via container name.
                            target_url = f"http://{container_name}:{target_port}"
                            print(f"Docker Monitor: Container {container_name} ({container_id}) using internal network: {target_url}")
                            break
                else:
                    print(f"Docker Monitor: No port binding found for {target_port} on {container_name} ({container_id}).")
                    return
            else:
                print(f"Docker Monitor: No ports exposed on {container_name} ({container_id}).")
                return
        except KeyError:
            print(f"Docker Monitor: Could not determine network settings for {container_name} ({container_id}).")
            return

        if not target_url:
            print(f"Docker Monitor: Could not determine target URL for {container_name} ({container_id}).")
            return

        if action == "start":
            await global_registry.register_service(hostname, target_url, f"Docker Container: {container_name} ({container_id})")
            print(f"Docker Monitor: Registered {hostname} -> {target_url} for {container_name} ({container_id}).")
        elif action == "die":
            await global_registry.unregister_service_by_container_id(container_id)
            print(f"Docker Monitor: Unregistered services for container {container_name} ({container_id}).")
    except Exception as e:
        print(f"Docker Monitor: Error processing container {container_name} ({container_id}): {e}")

async def watch_docker_events():
    """
    Monitors Docker events for container starts and stops to dynamically update the service registry.
    """
    global _monitor_task_should_stop, _monitor_task_active
    _monitor_task_active = True
    print("Docker Monitor: Starting event watcher...")

    try:
        docker_client = docker.from_env()
        while not _monitor_task_should_stop.is_set():
            try:
                async for event in docker_client.events(decode=True):
                    if _monitor_task_should_stop.is_set():
                        break

                    if event["Type"] == "container":
                        action = event["Action"]
                        container = docker_client.containers.get(event["id"])
                        if action in ("start", "die"):
                            await process_container_labels(container, action)
                        else:
                            print(f"Docker Monitor: Ignoring container event {action} for {event['id'][:12]}.")

            except docker.errors.APIError as e:
                print(f"Docker Monitor: APIError in event stream: {e}. Attempting to reconnect...")
                await asyncio.sleep(5)  # Wait before retrying
            except Exception as e:
                print(f"Docker Monitor: Error in event stream: {e}. Restarting event watcher.")
    finally:
        print("Docker Monitor: Event watcher stopped.")
        _monitor_task_active = False
        _monitor_task_should_stop.clear()