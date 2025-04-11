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
    Initializes a default config.yml file.
    """
    default_config = models.MoatSettings(secret_key="YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE", moat_base_url="http://localhost", cookie_domain="localhost").model_dump(exclude_unset=True) # Example values
    
    if config.CONFIG_FILE_PATH.exists():
        typer.confirm(f"{config.CONFIG_FILE_PATH} already exists. Overwrite?", abort=True)
    
    _save_config_yaml_dict(default_config)
    typer.secho(f"Default configuration written to {config.CONFIG_FILE_PATH}", fg=typer.colors.GREEN)

@app_cli.command()
def run():
    """
    Runs the Moat server.
    """
    uvicorn.run("moat.server:app", host=config.get_settings().listen_host, port=config.get_settings().listen_port, reload=False)

@app_cli.command()
def create_user(username: str = typer.Argument(..., help="The username to create.")):
    """
    Creates a new user in the database.