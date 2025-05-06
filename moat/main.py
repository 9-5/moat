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
    Initialize a default config.yml file if one doesn't exist.
    """
    if config.CONFIG_FILE_PATH.exists():
        typer.secho("Config file already exists. Doing nothing.", fg=typer.colors.YELLOW)
    else:
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
        typer.secho("Default config.yml created. Please edit it.", fg=typer.colors.GREEN)

@app_cli.command()
def run(
    reload: bool = typer.Option(False, help="Enable auto-reload for development."),
    host: