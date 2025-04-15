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
    reload: bool = typer.Option(False, help="Enable auto-reload for development."),
    host: str = typer.Option(None, help="Override listen_host from config.yml."),
    port: int = typer.Option(None, help="Override listen_port from config.yml.")
):
    """Runs the Moat server."""
    cfg = config.get_settings()

    # Override host/port from CLI if provided
    listen_host = host if host is not None else cfg.listen_host
    listen_port = port if port is not None else cfg.listen_port

    uvicorn.run("moat.server:app", host=listen_host, port=listen_port, reload=reload)

@app_cli.command()
def init_config():
    """Initializes a default config.yml if one does not exist."""
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
        _save_config_yaml_dict(default_config)
        typer.secho("Default config.yml created. Please edit it!", fg=typer.colors.GREEN)
    else:
        typer.secho("config.yml already exists!", fg=typer.colors.YELLOW)

@app_cli.command()
def create_user(username: str = typer.Option(...), password: str = typer.Option(...)):
    """Creates a new user in the database."""
    async def _create_user(username, password):
        try:
            await database.init_db()  # Ensure database is initialized
            user = models.User(username=username)
            await database.create_user_db(user, password)
            typer.secho(f"User '{username}' created successfully.", fg=typer.colors.GREEN)
        except ValueError as e:
            typer.secho(str(e), fg=typer.colors.RED)
        except Exception as e:
            typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)
    asyncio.run(_create_user(username, password))

@app_cli.command()
def docker_bind(
    container_name: str = typer.Option(...),
    public_hostname: str = typer.Option(...)
):
    """Binds a Docker container's port to a public hostname using static service configuration."""
    
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
    except DockerNotFound:
        typer.secho(f"Container '{container_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error connecting to Docker: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    cfg_dict = _load_config_yaml_dict()
    if not cfg_dict:
        typer.secho("Error: config.yml is empty or invalid.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Get container port from labels, or prompt user
    container_port = None
    moat_label_prefix = cfg_dict.get('moat_label_prefix', 'moat') # default to 'moat'
    port_label_name = f"{moat_label_prefix}.port"
    if container.labels and port_label_name in container.labels:
        container_port = container.labels[port_label_name]
        typer.secho(f"Using port '{container_port}' from container label '{port_label_name}'.", fg=typer.colors.CYAN)
    else:
        container_port = typer.prompt("Enter the container's port to expose")

    try:
        container_port = int(container_port)
    except ValueError:
        typer.secho("Invalid port number.", fg=typer.colors.RED)
        raise typer.Exit()

    # Get container IP address
    try:
        container_ip = container.attrs['NetworkSettings']['Networks']['bridge']['IPAddress']
    except KeyError:
        typer.secho("Could not determine container IP address.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    final_target_url = f"http://{container_ip}:{container_port}"

    # Check if service already exists
    existing_service = next((s for s in cfg_dict['static_services'] if s.get('hostname') == public_hostname), None)
    if existing_service:
        typer.secho(f"Warning: Service '{public_hostname}' already exists.", fg=typer.colors.YELLOW)
        if typer.confirm("Do you want to update the target URL?"):
            existing_service['target_url'] = final_target_url
            existing_service['_comment'] = f"Bound to Docker container: {container.name} (ID: {container.short_id}) via docker:bind"
            _save_config_yaml_dict(cfg_dict)
            typer.secho(f"Static service '{public_hostname}' updated.", fg=typer.colors.GREEN)
        else:
            typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    new_service_entry = {
        "hostname": public_hostname,
        "target_url": final_target_url,
        "_comment": f"Bound to Docker container: {container.name} (ID: {container.short_id}) via docker:bind"
    }
    cfg_dict['static_services'].append(new_service_entry)
    
    _save_config_yaml_dict(cfg_dict)
    typer.secho(f"Static service '{public_hostname}' -> '{final_target_url