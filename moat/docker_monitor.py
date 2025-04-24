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
    labels = container.labels
    
    enable_label = f"{cfg.moat_label_prefix}.enable"
    hostname_label = f"{cfg.moat_label_prefix}.hostname"
    port_label = f"{cfg.moat_label_prefix}.port"

    if enable_label in labels and labels[enable_label].lower() == "true":
        hostname = labels.get(hostname_label)
        port = labels.get(port_label)
        
        if not hostname or not port:
            print(f"Docker Monitor: Container {container.name} has 'enable' label but missing 'hostname' or 'port', skipping.")
            return
        
        try:
            target_url = f"http://{container.name}:{port}"  # Internal Docker network URL
            print(f"Docker Monitor: Registering {hostname} -> {target_url} for container {container.name} (action: {action})")
            if action == "start":
                await global_registry.register_service(hostname, target_url)
            elif action == "die":
                await global_registry.remove_service(hostname) # Ensure removal on container stop
        except Exception as e:
            print(f"Docker Monitor: Error processing labels for {container.name}: {e}")
    else:
        if action == "die":
            hostname_label = f"{cfg.moat_label_prefix}.hostname"
            hostname = labels.get(hostname_label)
            if hostname:
                 await global_registry.remove_service(hostname) # Ensure removal on container stop
        else:
             print(f"Docker Monitor: Container {container.name} does not have '{cfg.moat_label_prefix}.enable=true', skipping.")
            

async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    
    if _monitor_task_active:
        print("Docker Monitor: Already running, stop first.")
        return
    
    print("Docker Monitor: Starting event watcher...")
    _monitor_task_active = True
    
    try:
        client = docker.from_env()
        async for event in client.events(decode=True):
            if _monitor_task_should_stop.is_set():
                print("Docker Monitor: Exiting event watcher loop.")
                break

            if event['Type'] == 'container':
                action = event['Action']
                try:
                    container = client.containers.get(event["id"])

                    if action in ("start", "die"):
                        await process_container_labels(container, action)
                    elif action == "destroy":
                        hostname_label = f"{get_settings().moat_label_prefix}.hostname"
                        if 'Labels' in event and hostname_label in event['Labels']:
                            hostname = event['Labels'][hostname_label]
                            await global_registry.remove_service(hostname)
                        else:
                            print(f"Docker Monitor: Container {event['id'][:12]} not found for event {action}, skipping.")
                    except NotFound:

                        print(f"Docker Monitor: Container {event['id'][:12]} not found, skipping.")
                except Exception as e:
                    print(f"Docker Monitor: Error processing event for {event['id'][:12]}: {e}")
            else:
                print(f"Docker Monitor: Unknown event action: {action}")

    except docker.errors.DockerException as e:
        print(f"Docker Monitor: DockerException in event stream: {e}. Is Docker running and accessible? Stopping monitor.")
    except Exception as e:
        print(f"Docker Monitor: Error in event stream: {e}. Stopping monitor.")
    finally:
        print("Docker Monitor: Event watcher stopped.")
        _monitor_task_active = False
        _monitor_task_should_stop.clear()