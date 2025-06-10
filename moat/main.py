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
def init_config(force: bool = typer.Option(False, "--force", help="Overwrite existing config file if it exists.")):
    """
    Initializes a default config.yml file.
    """
    if config.CONFIG_FILE_PATH.exists() and not force:
        typer.secho("config.yml already exists. Use --force to overwrite.", fg=typer.colors.YELLOW)
        raise typer.Exit()

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

    _save_config_yaml_dict(default_config)
    typer.secho("config.yml created with default settings.  Please review and update!", fg=typer.colors.GREEN)

@app_cli.command()
def add_user(username: str):
    """
    Adds a new user to the database.
    """
    import getpass

    if not username:
        typer.secho("Username cannot be empty.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm Password: ")

        if password != password_confirm:
            typer.secho("Passwords do not match.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        asyncio.run(database.create_user_db(models.User(username=username), password))
        typer.secho(f"User '{username}' added successfully.", fg=typer.colors.GREEN)

    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(code=1)

@app_cli.command()
def run(reload: bool = typer.Option(False, "--reload", help="Enable auto-reload on code changes (development only).")):
    """
    Runs the Moat server.
    """
    uvicorn.run("moat.server:app", host="0.0.0.0",