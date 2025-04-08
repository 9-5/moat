import typer
import uvicorn
import asyncio
from pathlib import Path
import yaml
import docker
from docker.errors import NotFound as DockerNotFound # type: ignore
from typing import Optional

from moat import server, config, database, models
app_cli = typer.Typer()

# Helper for CLI to load config.yml as dict
def _load_config_yaml_dict() -> dict:
    if config.CONFIG_FILE_PATH.exists():
        with open(config.CONFIG_FILE_PATH, 'r') as f:
            return yaml.safe_load(f) or {} # return empty dict if file is empty
    return {}

# Helper for CLI to save config.yml from dict
def _save_config_yaml_dict(config_data: dict):
    with open(config.CONFIG_FILE_PATH, 'w') as f:
        yaml.dump(config_data, f, sort_keys=False, default_flow_style=False)

@app_cli.command()
def init_config():
    """
    Initialize a default config.yml if one does not exist.
    """
    if config.CONFIG_FILE_PATH.exists():
        typer.secho("Config file already exists. Doing nothing.", fg=typer.colors.YELLOW)
    else:
        default_config = """
listen_host: "0.0.0.0"
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE" # Generate with: openssl rand -hex 32
access_token_expire_minutes: 60
database_url: "sqlite+aiosqlite:///./moat.db"

# Public base URL for Moat's auth pages (e.g., "https://moat.yourdomain.com")
# Required if Moat itself is behind a reverse proxy or tunnel on a different URL than it listens on.
moat_base_url: null

# Cookie domain for SSO (e.g., ".yourdomain.com" or a specific hostname)
# Ensure this matches how your applications are accessed.
cookie_domain: null

# Docker label monitoring settings
docker_monitor_enabled: true
moat_label_prefix: "moat" # e.g., moat.enable, moat.hostname

# Static service definitions (useful for non-Docker services or fixed targets)
static_services:
#  - hostname: "service1.localhost"
#    target_url: "http://127.0.0.1:9001"
#  - hostname: "another.example.com"
#    target_url: "http://192.168.1.100:8080"
"""
        with open(config.CONFIG_FILE_PATH, 'w') as f:
            f.write(default_config)
        typer.secho("Default config.yml created.  Edit this file!", fg=typer.colors.GREEN)

@app_cli.command()
def run(
    reload: bool = typer.Option(False, help="Enable auto-reload on code changes.  Development only!"),
    port: int = typer.Option(None, help="Port to listen on. Overrides config.yml."),
    host: str = typer.Option(None, help="Host to listen on. Overrides config.yml.")
):
    """
    Run the Moat server.
    """
    cfg_dict = _load_config_yaml_dict()

    uvicorn_kwargs = {
        "app": "moat.server:app",
        "host": host or cfg_dict.get('listen_host', '0.0.0.0'),
        "port": port or cfg_dict.get('listen_port', 8000),
    }
    if reload:
        uvicorn_kwargs["reload"] = True
        typer.secho("Auto-reload enabled.  Do not use in production!", fg=typer.colors.YELLOW)

    uvicorn.run(**uvicorn_kwargs)

@app_cli.command()
def add_static(
    public_hostname: str = typer.Argument(..., help="The public hostname (e.g., app.example.com)"),
    target_url: str = typer.Argument(..., help="The target URL (e.g., http://127.0.0.1:8000)")
):
    """
    Add a static service (one that is not dynamically discovered).
    """
    cfg_dict = _load_config_yaml_dict()

    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Check if the service already exists.
    existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == public_hostname), None)
    if existing_service:
        typer.secho(f"Service '{public_hostname}' already exists:", fg=typer.colors.YELLOW)
        typer.echo(f"  Hostname: {existing_service['hostname']}")
        typer.echo(f"  Target URL: {existing_service['target_url']}")
        if typer.confirm("Overwrite?"):
            existing_service['target_url'] = target_url
            _save_config_yaml_dict(cfg_dict)
            typer.secho(f"Static service '{public_hostname}' updated.", fg=typer.colors.GREEN)
        else:
            typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    new_service_entry = {
        "hostname": public_hostname,
        "target_url": target_url
    }
    cfg_dict['static_services'].append(new_service_entry)
    
    _save_config_yaml_dict(cfg_dict)
    typer.secho(f"Static service '{public_hostname}' -> '{target_url}' added.", fg=typer.colors.GREEN)

@app_cli.command()
def bind_docker(
    container_name: str = typer.Argument(..., help="The name of the Docker container."),
    public_hostname: str = typer.Argument(..., help="The public hostname to associate with the container (e.g., app.example.com).")
):
    """
    Dynamically binds a Docker container to a public hostname, creating a static service entry.

    It retrieves the container's internal port from its labels (e.g., 'moat.port') and 
    creates a static service entry in the config.yml, pointing the public hostname to the container.
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        typer.secho(f"Container '{container_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit()
    except docker.errors.APIError as e:
        typer.secho(f"Error connecting to Docker API: {e}", fg=typer.colors.RED)
        raise typer.Exit()

    cfg_dict = _load_config_yaml_dict()

    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Construct the target URL from the container's network settings
    container_network_settings = container.attrs['NetworkSettings']
    if not container_network_settings or not container_network_settings['Networks']:
        typer.secho(f"Container '{container.name}' does not seem to be attached to a network.", fg=typer.colors.RED)
        raise typer.Exit()

    # Get the first network's IP address.
    network_name = list(container_network_settings['Networks'].keys())[0]
    container_ip = container_network_settings['Networks'][network_name]['IPAddress']
    if not container_ip:
        typer.secho(f"Container '{container.name}' has no IP address in network '{network_name}'.", fg=typer.colors.RED)
        raise typer.Exit()

    # Find the exposed port from container labels or prompt
    moat_label_prefix = cfg_dict.get('moat_label_prefix', 'moat')
    port_label = f"{moat_label_prefix}.port"
    exposed_port = container.labels.get(port_label)

    if not exposed_port:
        typer.secho(f"Container '{container.name}' does not have label '{port_label}'.", fg=typer.colors.RED)
        exposed_port = typer.prompt(f"Please enter the container's internal port to expose for container '{container.name}'", type=int) # Prompt if not found
        exposed_port = str(exposed_port) # Convert to string

    final_target_url = f"http://{container_ip}:{exposed_port}"

    # Check if the service already exists.
    existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == public_hostname), None)
    if existing_service:
        typer.secho(f"Service '{public_hostname}' already exists:", fg=typer.colors.YELLOW)
        typer.echo(f"  Hostname: {existing_service['hostname']}")
        typer.echo(f"  Target URL: {existing_service['target_url']}")

        if typer.confirm(f"Overwrite with binding to container '{container.name}' (IP: {container_ip}, Port: {exposed_port})?"):
            # Remove the existing service (have to loop because you can't delete during iteration)
            for i, existing_service in enumerate(cfg_dict['static_services']):
                if existing_service['hostname'] == public_hostname:
                    del cfg_dict['static_services'][i]
                    break # exit the loop
            else:
                pass # pragma: no cover

            existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == public_hostname), None)  # Re-check

            if existing_service is not None:
              del cfg_dict['static_services'][existing_service)  # Remove old entry
            else:
                typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
                raise typer.Exit()
            break # exit the loop - ensures only one overwrite

    # Inspect container labels for port
    moat_label_prefix = cfg_dict.get('moat_label_prefix', 'moat')
    port_label = f"{moat_label_prefix}.port"
    exposed_port = container.labels.get(port_label)

    if not exposed_port:
        typer.secho(f"Container '{container.name}' does not have label '{port