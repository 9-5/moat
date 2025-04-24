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
    Initialize a default config.yml file.
    """
    if config.CONFIG_FILE_PATH.exists():
        typer.confirm(f"{config.CONFIG_FILE_PATH} already exists. Overwrite?", abort=True)

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
    _save_config_yaml_dict(default_config)
    typer.secho(f"Default config created at {config.CONFIG_FILE_PATH}", fg=typer.colors.GREEN)

@app_cli.command()
def add_user(username: str):
    """
    Add a new user to the database.
    """
    import getpass
    try:
        asyncio.run(database.init_db()) # Ensure DB exists
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")

        if password != password_confirm:
            typer.secho("Passwords do not match.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        user = models.User(username=username)
        asyncio.run(database.create_user_db(user, password))
        typer.secho(f"User '{username}' added successfully.", fg=typer.colors.GREEN)

    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

@app_cli.command()
def run(
    reload: bool = typer.Option(False, help="Enable auto-reload for development."),
    port: int = typer.Option(None, help="Port to listen on. Overrides config.yml."),
    host: str = typer.Option(None, help="Host to bind to. Overrides config.yml.")
):
    """
    Run the Moat server.
    """
    cfg = config.get_settings()
    
    # Override from CLI if provided
    listen_port = port if port is not None else cfg.listen_port
    listen_host = host if host is not None else cfg.listen_host

    uvicorn.run(server.app, host=listen_host, port=listen_port, reload=reload)

@app_cli.command()
def add_static(public_hostname: str, target_url: str):
    """
    Add a static service entry to config.yml.
    """
    cfg_dict = _load_config_yaml_dict()
    if not isinstance(cfg_dict, dict):
        typer.secho("config.yml is invalid or empty.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    if 'static_services' not in cfg_dict or not isinstance(cfg_dict['static_services'], list):
        cfg_dict['static_services'] = []
    
    # Check if service already exists, prompt to update
    for i, service in enumerate(cfg_dict['static_services']):
        if service.get('hostname') == public_hostname:
            if typer.confirm(f"Service '{public_hostname}' already exists. Update target URL to '{target_url}'?", default=True):
                cfg_dict['static_services'][i]['target_url'] = target_url
                _save_config_yaml_dict(cfg_dict)
                typer.secho(f"Static service '{public_hostname}' updated.", fg=typer.colors.GREEN)
            else:
                typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
            raise typer.Exit()
    
    new_service_entry = {"hostname": public_hostname, "target_url": target_url}
    cfg_dict['static_services'].append(new_service_entry)
    _save_config_yaml_dict(cfg_dict)
    typer.secho(f"Static service '{public_hostname}' -> '{target_url}' added.", fg=typer.colors.GREEN)

@app_cli.command()
def add_docker_bind(public_hostname: str, container_name: str):
    """
    Add a static service entry, bound to a docker container by name.

    This command introspects the container's exposed ports and attempts to
    create a suitable static service entry pointing to the container's internal
    network. It requires Docker to be running and accessible.
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        typer.secho(f"Container '{container_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except docker.errors.APIError as e:
        typer.secho(f"Error connecting to Docker API: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    ports = container.ports
    if not ports:
        typer.secho(f"Container '{container_name}' does not expose any ports.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # For simplicity, pick the first exposed port.  A more sophisticated
    # implementation might allow the user to specify which port to use.
    first_port = list(ports.keys())[0].split('/')[0] # handle tcp/udp