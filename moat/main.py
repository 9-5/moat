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
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development.")
):
    """
    Run the Moat server.
    """
    uvicorn.run("moat.server:app", host=host, port=port, reload=reload)

@app_cli.command()
def init_config():
    """
    Initialize a default config.yml file if one doesn't exist.
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
        typer.secho("config.yml already exists.", fg=typer.colors.YELLOW)

@app_cli.command()
def create_user(username: str = typer.Option(..., prompt="Username"), password: str = typer.Option(..., prompt="Password", hide_input=True, confirmation_prompt=True)):
    """
    Create a new user in the database.
    """
    async def _create_user(username, password):
        try:
            await database.init_db()
            user_data = models.User(username=username)
            await database.create_user_db(user_data, password)
            typer.secho(f"User {username} created successfully.", fg=typer.colors.GREEN)
        except ValueError as e:
            typer.secho(str(e), fg=typer.colors.RED)
        except Exception as e: