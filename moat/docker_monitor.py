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
remove_service_by_container_id(event["id"])
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