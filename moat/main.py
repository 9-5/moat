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
    host: str = typer.Option("0.0.0.0", help="Host for the app"),
    port: int = typer.Option(8000, help="Port for the app"),
    reload: bool = typer.Option(False, help="Enable auto-reload (for development)")
):
    """
    Run the Moat server.
    """
    uvicorn.run("moat.server:app", host=host, port=port, reload=reload)

@app_cli.command()
def init_config():
    """
    Initialize a default config.yml if one does not exist.
    """
    if not config.CONFIG_FILE_PATH.exists():
        default_config = {
            "listen_host": "0.0.0.0",
            "listen_port": 8000,
            "secret_key": "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE", # Generate with: openssl rand -hex 32
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
        typer.secho("Default config.yml created. Please edit it!", fg=typer.colors.GREEN)
    else:
        typer.secho("config.yml already exists!", fg=typer.colors.YELLOW)

@app_cli.command()
def add_user(username: str = typer.Option(..., prompt="Username"), password: str = typer.Option(..., prompt="Password", hide_input=True, confirmation_prompt=True)):
    """
    Add a user to the Moat database.
    """
    try:
        asyncio.run(database.init_db())
        user = models.User(username=username)
        asyncio.run(database.create_user_db(user, password))
        typer.secho(f"User {username} created successfully.", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)

@app_cli.command()
def add_static_service(
    public_hostname: str = typer.Option(..., help="The public hostname for the service"),
    target_url: str = typer.Option(..., help="The target URL for the service"),
):
    """
    Add a static service to Moat's configuration.
    """
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Check if the service already exists
    existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == public_hostname), None)
    if existing_service:
        if typer.confirm(f"Service '{public_hostname}' already exists. Overwrite?"):
            existing_service['target_url'] = target_url
            _save_config_yaml_dict(cfg_dict)
            typer.secho(f"Static service '{public_hostname}' updated.", fg=typer.colors.GREEN)
        else:
            typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
        return

    new_service_entry = {
        "hostname": public_hostname,
        "target_url": target_url
    }
    cfg_dict['static_services'].append(new_service_entry)
    _save_config_yaml_dict(cfg_dict)
    typer.secho(f"Static service '{public_hostname}' -> '{target_url}' added.", fg=typer.colors.GREEN)

@app_cli.command()
def add_docker_static_service(
    container_name: str = typer.Option(..., help="The name or ID of the Docker container"),
    public_hostname: str = typer.Option(..., help="The public hostname for the service"),
    container_port: int = typer.Option(..., help="The port exposed by the Docker container"),
):
    """
    Add a static service, bound to a docker container's internal network, to Moat's configuration.
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
    except DockerNotFound:
        typer.secho(f"Container '{container_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit()

    final_target_url = f"http://{container.name}:{container_port}" # e.g. http://my-app:8080

    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Check if the service already exists
    existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == public_hostname), None)
    if existing_service:
        if typer.confirm(f"Service '{public_hostname}' already exists. Over