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
    host: str = typer.Option("0.0.0.0", help="Host for the Moat server"),
    port: int = typer.Option(8000, help="Port for the Moat server"),
    reload: bool = typer.Option(False, help="Enable auto-reloading (for development)")
):
    """
    Runs the Moat server.
    """
    uvicorn.run("moat.server:app", host=host, port=port, reload=reload)

@app_cli.command()
def init_config():
    """
    Initializes a default config.yml file if one doesn't exist.
    """
    if config.CONFIG_FILE_PATH.exists():
        typer.secho("Config file already exists!", fg=typer.colors.YELLOW)
    else:
        default_config = {
            "listen_host": "0.0.0.0",
            "listen_port": 8000,
            "secret_key": "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE",  # Generate with: openssl rand -hex 32
            "access_token_expire_minutes": 60,
            "database_url": "sqlite+aiosqlite:///./moat.db",
            "moat_base_url": None,
            "cookie_domain": None,
            "login_url": None,
            "logout_url": None,
            "docker_monitor_enabled": True,
            "moat_label_prefix": "moat",
            "static_services": []
        }
        _save_config_yaml_dict(default_config)
        typer.secho("Config file created! Please edit config.yml.", fg=typer.colors.GREEN)

@app_cli.command()
def create_user(username: str):
    """
    Creates a new user in the database.
    """
    password = typer.prompt("Enter password for user", hide_input=True)
    password_confirm = typer.prompt("Confirm password", hide_input=True)
    if password != password_confirm:
        typer.secho("Passwords do not match!", fg=typer.colors.RED)
        raise typer.Exit()

    async def _create_user(username, password):
        try:
            await database.init_db()
            user_data = models.User(username=username)
            await database.create_user_db(user_data, password)
            typer.secho(f"User {username} created successfully!", fg=typer.colors.GREEN)
        except ValueError as e:
            typer.secho(str(e), fg=typer.colors.RED)
        except Exception as e:
            typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)

    asyncio.run(_create_user(username, password))

@app_cli.command()
def add_static_service(public_hostname: str, target_url: str):
    """
    Adds a static service to the Moat configuration.
    """
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Check if a service with the same hostname already exists
    existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == public_hostname), None)

    if existing_service:
        typer.secho(f"A service with hostname '{public_hostname}' already exists.", fg=typer.colors.YELLOW)
        if typer.confirm("Do you want to update the target URL?"):
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
def bind_static_service(public_hostname: str, container_name: str):
    """
    Binds a static service to a Docker container, automatically setting the target URL.
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
    except DockerNotFound:
        typer.secho(f"Container '{container_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit()
    except Exception as e:
        typer.secho(f"Error connecting to Docker: {e}", fg=typer.colors.RED)
        raise typer.Exit()

    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Determine the target URL from the container's labels, or prompt if not available.
    moat_label_prefix = cfg_dict.get("moat_label_prefix