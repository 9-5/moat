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
        yaml.dump(config_data, f, sort_keys=False, default_flow_style=False, indent=2)

@app_cli.command()
def run(
    host: str = typer.Option("0.0.0.0", help="Host for the app"),
    port: int = typer.Option(8000, help="Port for the app"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development")
):
    """Runs the Moat server."""
    uvicorn.run("moat.server:app", host=host, port=port, reload=reload)

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
        typer.secho("config.yml already exists.", fg=typer.colors.YELLOW)

@app_cli.command()
def add_static_service(
    public_hostname: str = typer.Option(..., help="The public hostname for the service (e.g., app.example.com)"),
    target_url: str = typer.Option(..., help="The target URL the hostname should proxy to (e.g., http://localhost:9000)"),
):
    """Adds a static service entry to the config.yml."""
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []
    
    # Check if the service already exists
    existing_service = next((s for s in cfg_dict['static_services'] if s.get('hostname') == public_hostname), None)
    if existing_service:
        typer.secho(f"Service '{public_hostname}' already exists.  Update? (y/n)", fg=typer.colors.YELLOW)
        if typer.confirm(""):
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
def add_docker_binding(
    container_name_or_id: str = typer.Option(..., help="The name or ID (or short ID) of the Docker container"),
    public_hostname: str = typer.Option(..., help="The public hostname for the service (e.g., app.example.com)"),
    target_port: int = typer.Option(..., help="The port on the container that should be proxied"),
):
    """Adds a static service entry to the config.yml, bound to a Docker container's name.
    This facilitates simpler setup where Moat auto-discovers the container's IP."""
    
    try:
        client = docker.from_env()
        container = client.containers.get(container_name_or_id)
    except docker.errors.NotFound:
        typer.secho(f"Error: Container '{container_name_or_id}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    final_target_url = f"http://{container.name}:{target_port}"
    
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

   # Check if the service already exists
    existing_service = next((s for s in cfg_dict['static_services'] if s.get('hostname') == public_hostname), None)
    if existing_service:
        typer.secho(f"Service '{public_hostname}' already exists.  Update to bind to container '{container.name}'? (y/n)", fg=typer.colors.YELLOW)
        if typer.confirm(""):
            existing_service['target_url'] = final_target_url
            #Optionally update the _comment too if it exists
            if '_comment' in existing_service:
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
    typer.secho(f"Static service '{public_hostname}' -> '{final_target_url}' added for container '{container.name}'.", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app_cli()