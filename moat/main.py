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
def run(
    host: str = typer.Option("0.0.0.0", help="Host for the app to listen on."),
    port: int = typer.Option(8000, help="Port for the app to listen on."),
    reload: bool = typer.Option(False, help="Enable auto-reloading on code changes.  **FOR DEV PURPOSES ONLY**"),
    log_level: str = typer.Option("info", help="Log level for the application."),
):
    """
    Run the Moat server.
    """
    uvicorn.run("moat.server:app", host=host, port=port, reload=reload, log_level=log_level)

@app_cli.command()
def init_config():
    """
    Initialize a default config.yml if one does not exist.
    """
    if not config.CONFIG_FILE_PATH.exists():
        default_config = {
            "listen_host": "0.0.0.0",
            "listen_port": 8000,
            "secret_key": "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE",  # Generate with: openssl rand -hex 32
            "access_token_expire_minutes": 60,
            "database_url": "sqlite+aiosqlite:///./moat.db",
            "moat_base_url": None,
            "cookie_domain": None,
            "docker_monitor_enabled": True,
            "moat_label_prefix": "moat",
            "static_services": []
        }

        with open(config.CONFIG_FILE_PATH, 'w') as f:
            yaml.dump(default_config, f, sort_keys=False, default_flow_style=False)

        typer.secho("Default config.yml created.  Please edit this file to configure Moat.", fg=typer.colors.GREEN)
    else:
        typer.secho("config.yml already exists.  Doing nothing.", fg=typer.colors.YELLOW)

@app_cli.command()
def add_static(
    public_hostname: str = typer.Option(..., help="The public hostname for the service (e.g., app.example.com)."),
    target_url: str = typer.Option(..., help="The full target URL for the service (e.g., http://127.0.0.1:8080)."),
):
    """
    Add a static service to the config.yml.  Useful for services not running in Docker, or for fixed targets.
    """
    cfg_dict = _load_config_yaml_dict()

    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Basic validation to prevent duplicates (hostname must be unique)
    for existing_service in cfg_dict['static_services']:
        if existing_service['hostname'] == public_hostname:
            typer.secho(f"Error: A static service with the hostname '{public_hostname}' already exists.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    new_service_entry = {
        "hostname": public_hostname,
        "target_url": target_url
    }
    cfg_dict['static_services'].append(new_service_entry)
    _save_config_yaml_dict(cfg_dict)

    typer.secho(f"Static service '{public_hostname}' -> '{target_url}' added.", fg=typer.colors.GREEN)

@app_cli.command()
def bind_docker(
    public_hostname: str = typer.Option(..., help="The public hostname for the service (e.g., app.example.com)."),
    container_name_or_id: str = typer.Option(..., help="The name OR ID of the Docker container to bind to."),
):
    """
    Add a static service to the config, dynamically bound to a Docker container.
    This command introspects the container to determine the internal port, so the target URL is generated automatically.
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_name_or_id)
    except DockerNotFound:
        typer.secho(f"Error: Docker container '{container_name_or_id}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error connecting to Docker: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Check for existing service by hostname to prevent duplicates
    for existing_service in cfg_dict['static_services']:
        if existing_service['hostname'] == public_hostname:
            typer.secho(f"A service with hostname '{public_hostname}' already exists.", fg=typer.colors.YELLOW)
            if typer.confirm("Overwrite it?", default=False):
                 cfg_dict['static_services'].remove(existing_service)  # Remove old entry
            else:
                typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
                raise typer.Exit()
            break # exit the loop - ensures only one overwrite

    # Inspect container labels for port
    moat_label_prefix = cfg_dict.get('moat_label_prefix', 'moat')
    port_label = f"{moat_label_prefix}.port"
    exposed_port = container.labels.get(port_label)

    if not exposed_port:
        typer.secho(f"Container '{container.name}' does not have label '{port_label}'.", fg=typer.colors.RED)
        exposed_port = typer.prompt(f"Please enter the container's internal port to expose for container '{container.name}'", type=int) # Prompt if not found
        exposed_port = str(