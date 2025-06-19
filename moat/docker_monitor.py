import asyncio
import docker # type: ignore
from docker.errors import NotFound, APIError # type: ignore
from typing import Optional, Any
import functools

from .service_registry import registry as global_registry
from .config import get_settings

_monitor_task_should_stop = asyncio.Event()
_monitor_task_active = False
_event_processing_task_ref: Optional[asyncio.Task] = None
_event_listener_manager_task_ref: Optional[asyncio.Task] = None

async def stop_docker_monitor_task():
    global _monitor_task_should_stop, _monitor_task_active
    global _event_processing_task_ref, _event_listener_manager_task_ref

    if not _monitor_task_should_stop.is_set():
        print("Docker Monitor: Stop signal received. Initiating shutdown of tasks...")
        _monitor_task_should_stop.set()
    else:
        _monitor_task_active = False # Ensure active is false if stop already in progress
        return

    listener_task = _event_listener_manager_task_ref
    processor_task = _event_processing_task_ref

    _event_listener_manager_task_ref = None
    _event_processing_task_ref = None

    if listener_task and not listener_task.done():
        listener_task.cancel()
        try:
            await asyncio.wait_for(listener_task, timeout=3.0)
        except asyncio.CancelledError: pass
        except asyncio.TimeoutError:
            print("Docker Monitor: Timeout waiting for event listener manager task to complete on stop.")
        except Exception as e:
            print(f"Docker Monitor: Error stopping listener manager task: {e}")

    if processor_task and not processor_task.done():
        processor_task.cancel()
        try:
            await asyncio.wait_for(processor_task, timeout=2.0)
        except asyncio.CancelledError: pass
        except asyncio.TimeoutError:
            print("Docker Monitor: Timeout waiting for event processing task to complete on stop.")
        except Exception as e:
            print(f"Docker Monitor: Error stopping processing task: {e}")
    
    _monitor_task_active = False
    print("Docker Monitor: Shutdown sequence complete.")


async def is_docker_monitor_running() -> bool:
    global _monitor_task_active, _event_listener_manager_task_ref, _event_processing_task_ref
    if _monitor_task_active:
        listener_running = _event_listener_manager_task_ref and not _event_listener_manager_task_ref.done()
        processor_running = _event_processing_task_ref and not _event_processing_task_ref.done()
        if listener_running and processor_running:
            return True
        else:
            return False
    return False


async def process_container_labels(container_obj, action: str):
    cfg = get_settings()
    prefix = cfg.moat_label_prefix
    
    container_id = container_obj.id
    container_name = container_obj.name
    labels = container_obj.labels

    try:
        live_container_attrs = container_obj.attrs 
    except Exception as e:
        print(f"Docker Monitor: Error accessing attributes for {container_name} ({container_id[:12]}): {e}. Skipping.")
        if action in ["start", "unpause"]:
            await global_registry.remove_services_by_container_id(container_id)
        return

    if action in ["stop", "die", "pause"]:
        await global_registry.remove_services_by_container_id(container_id)
        return

    if action in ["start", "unpause"]:
        enable_label_key = f"{prefix}.enable"
        if labels.get(enable_label_key) != "true":
            await global_registry.remove_services_by_container_id(container_id)
            return

        hostname_val = labels.get(f"{prefix}.hostname")
        port_val_str = labels.get(f"{prefix}.port")
        scheme_val = labels.get(f"{prefix}.scheme", "http").lower()

        if not (hostname_val and port_val_str):
            print(f"Docker Monitor: {container_name} enabled but missing required labels. Ensuring removal. Labels: {labels}")
            await global_registry.remove_services_by_container_id(container_id)
            return
        
        if scheme_val not in ["http", "https"]: scheme_val = "http"

        try: internal_container_port = int(port_val_str)
        except ValueError:
            print(f"Docker Monitor: Invalid port '{port_val_str}' for {container_name}. Ensuring removal.")
            await global_registry.remove_services_by_container_id(container_id)
            return

        target_url_determined: Optional[str] = None
        network_settings = live_container_attrs.get("NetworkSettings", {})
        container_ports_info = network_settings.get("Ports", {})
        published_bindings = container_ports_info.get(f"{internal_container_port}/tcp")

        if published_bindings and isinstance(published_bindings, list):
            host_ip_to_use = "127.0.0.1"; host_port_to_use_str = None
            for b in published_bindings:
                if b.get("HostIp") == "127.0.0.1": host_port_to_use_str = b.get("HostPort"); break
            if not host_port_to_use_str:
                for b in published_bindings:
                    if b.get("HostIp") == "0.0.0.0": host_port_to_use_str = b.get("HostPort"); break
            if not host_port_to_use_str and published_bindings: host_port_to_use_str = published_bindings[0].get("HostPort")
            if host_port_to_use_str:
                try:
                    int(host_port_to_use_str)
                    target_url_determined = f"{scheme_val}://{host_ip_to_use}:{host_port_to_use_str}"
                    print(f"Docker Monitor: Using published port for {container_name} ({container_id[:12]}): {target_url_determined}")
                except ValueError: print(f"Docker Monitor: Invalid HostPort '{host_port_to_use_str}'. Fallback.")
        
        if not target_url_determined:
            target_url_determined = f"{scheme_val}://{container_name}:{internal_container_port}"
        
        if target_url_determined:
            await global_registry.add_service(hostname_val, target_url_determined, "docker", container_id)
        else:
            print(f"Docker Monitor: Could not determine target_url for {container_name}. Ensuring removal.")
            await global_registry.remove_services_by_container_id(container_id)


async def initial_scan_containers(loop: asyncio.AbstractEventLoop, docker_client: Any):
    if not get_settings().docker_monitor_enabled: return
    print("Docker Monitor: Performing initial scan...")
    try:
        running_containers = await loop.run_in_executor(None, functools.partial(docker_client.containers.list, filters={"status": "running"}))
        for container in running_containers:
            if _monitor_task_should_stop.is_set(): print("Docker Monitor: Initial scan aborted."); return
            await process_container_labels(container, "start")
    except APIError as e: print(f"Docker Monitor: Docker APIError during initial scan: {e}.")
    except Exception as e: print(f"Docker Monitor: Error during initial scan: {e}.")
    print("Docker Monitor: Initial scan complete.")


def _listen_for_docker_events_thread(queue: asyncio.Queue, stop_event: asyncio.Event, loop: asyncio.AbstractEventLoop):
    print("Docker Monitor (Thread): Listener started.")
    docker_client_thread = None
    try:
        docker_client_thread = docker.from_env()
        for event_data in docker_client_thread.events(decode=True): # This blocks
            if stop_event.is_set(): break
            try: asyncio.run_coroutine_threadsafe(queue.put(event_data), loop).result(timeout=1.0)
            except asyncio.TimeoutError:
                print("Docker Monitor (Thread): Timeout putting event on queue.")
                if stop_event.is_set(): break 
            except Exception as e: print(f"Docker Monitor (Thread): Error putting event: {e}"); break # Break on other put errors
    except APIError as e: print(f"Docker Monitor (Thread): Docker APIError: {e}. Thread stopping.")
    except Exception as e: print(f"Docker Monitor (Thread): Unexpected error: {e}. Thread stopping.")
    finally:
        if docker_client_thread:
            try: docker_client_thread.close()
            except: pass
        try: asyncio.run_coroutine_threadsafe(queue.put(None), loop).result(timeout=1.0) # Sentinel
        except: print("Docker Monitor (Thread): Error putting sentinel.")
        print("Docker Monitor (Thread): Listener stopped.")


async def _process_event_queue(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, docker_client: Any):
    print("Docker Monitor (Async Processor): Processor started.")
    while True:
        if _monitor_task_should_stop.is_set() and queue.empty(): break
        try: event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            if _monitor_task_should_stop.is_set(): break
            continue
        if event_data is None: break 

        try:
            event_type, action = event_data.get("Type"), event_data.get("Action")
            container_id = event_data.get("Actor", {}).get("ID")
            if event_type != "container" or not container_id or action not in ["start", "stop", "die", "pause", "unpause"]:
                queue.task_done(); continue
            try:
                container_obj = await loop.run_in_executor(None, functools.partial(docker_client.containers.get, container_id))
                await process_container_labels(container_obj, action)
            except NotFound:
                if action in ["stop", "die"]: await global_registry.remove_services_by_container_id(container_id)
            except APIError as e: print(f"Docker Monitor (Async Processor): APIError getting container {container_id[:12]}: {e}")
            except Exception as e: print(f"Docker Monitor (Async Processor): Error processing labels for {container_id[:12]}: {e}")
        except Exception as e: print(f"Docker Monitor (Async Processor): Error with event data: {e}")
        finally: queue.task_done()
    print("Docker Monitor (Async Processor): Processor stopped.")


async def _run_listener_thread_wrapper(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, stop_event: asyncio.Event):
    """Async wrapper to run the blocking listener thread in an executor."""
    try:
        await loop.run_in_executor(None, _listen_for_docker_events_thread, queue, stop_event, loop)
    except asyncio.CancelledError:
        stop_event.set() 
        raise
    except Exception as e:
        print(f"Docker Monitor (_run_listener_thread_wrapper): Exception in listener executor: {e}")
        stop_event.set()
        raise


async def watch_docker_events():
    global _monitor_task_should_stop, _monitor_task_active
    global _event_processing_task_ref, _event_listener_manager_task_ref

    loop = asyncio.get_running_loop()

    if _monitor_task_active or _event_listener_manager_task_ref or _event_processing_task_ref:
        print("Docker Monitor: watch_docker_events called while monitor may be running. Attempting to stop first.")
        await stop_docker_monitor_task()

    _monitor_task_should_stop.clear()
    _monitor_task_active = True 
    print("Docker Monitor: Starting event watcher manager...")

    if not get_settings().docker_monitor_enabled:
        print("Docker Monitor: Disabled by configuration.")
        _monitor_task_active = False; return

    docker_client_main = None
    try:
        docker_client_main = await loop.run_in_executor(None, docker.from_env)
        await initial_scan_containers(loop, docker_client_main)

        if _monitor_task_should_stop.is_set():
            print("Docker Monitor: Stopping after initial scan due to signal.")
            _monitor_task_active = False
            if docker_client_main: await loop.run_in_executor(None, docker_client_main.close)
            return

        event_queue = asyncio.Queue(maxsize=100)

        _event_listener_manager_task_ref = loop.create_task(
            _run_listener_thread_wrapper(loop, event_queue, _monitor_task_should_stop),
            name="DockerEventListenerManager"
        )
        _event_processing_task_ref = loop.create_task(
            _process_event_queue(event_queue, loop, docker_client_main),
            name="DockerEventProcessor"
        )
        print("Docker Monitor: Listener and processor tasks started.")

        current_tasks = []
        if _event_listener_manager_task_ref: current_tasks.append(_event_listener_manager_task_ref)
        if _event_processing_task_ref: current_tasks.append(_event_processing_task_ref)
        
        if not current_tasks: # Should not happen if tasks were created
            print("Docker Monitor: No tasks to wait for. Exiting manager.")
            _monitor_task_active = False
            if docker_client_main: await loop.run_in_executor(None, docker_client_main.close)
            return

        done, pending = await asyncio.wait(current_tasks, return_when=asyncio.FIRST_COMPLETED)
        
        _monitor_task_should_stop.set() 

        for task in pending:
            if not task.done():
                task.cancel()
                try: await asyncio.wait_for(task, timeout=2.0)
                except: pass 

        for task in done:
            if task.exception() and not isinstance(task.exception(), asyncio.CancelledError):
                print(f"Docker Monitor: Monitored sub-task {task.get_name()} failed: {task.exception()}")

    except APIError as e: print(f"Docker Monitor: Critical Docker APIError in watcher setup: {e}.")
    except Exception as e: print(f"Docker Monitor: Critical unexpected error in watcher manager: {e}")
    finally:
        print("Docker Monitor: Watcher manager finishing...")
        _monitor_task_active = False 
        _monitor_task_should_stop.set()

        # Final cleanup attempt, referencing local copies that were snapshotted if global refs were cleared
        tasks_to_finalize_final_attempt = []
        # Check original global refs if they haven't been cleared by a successful stop_docker_monitor_task call
        final_listener_task = _event_listener_manager_task_ref 
        final_processor_task = _event_processing_task_ref
        
        if final_listener_task and not final_listener_task.done(): tasks_to_finalize_final_attempt.append(final_listener_task)
        if final_processor_task and not final_processor_task.done(): tasks_to_finalize_final_attempt.append(final_processor_task)

        for task in tasks_to_finalize_final_attempt:
            task.cancel()
            try: await asyncio.wait_for(task, timeout=1.0)
            except: pass
        
        # Ensure global references are cleared if not already
        _event_listener_manager_task_ref = None
        _event_processing_task_ref = None

        if docker_client_main:
            try: await loop.run_in_executor(None, docker_client_main.close)
            except: pass
        print("Docker Monitor: Watcher manager fully stopped.")
