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
def run(reload: bool = False):
    """
    Run the Moat server.
    """
    asyncio.run(database.init_db()) # Initialize database
    uvicorn.run("moat.server:app", host="0.0.0.0", port=8000, reload=reload)

@app_cli.command()
def init_config():
    """
    Initializes a default config.yml file.
    """
    if config.CONFIG_FILE_PATH.exists():
        typer.confirm(f"Config file '{config.CONFIG_FILE_PATH}' already exists. Overwrite?", abort=True)

    # Use the Pydantic model to get default values.
    default_settings = models.MoatSettings(secret_key="YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE") # Provide dummy secret key
    
    # Convert the Pydantic model to a dictionary.
    config_data = default_settings.model_dump()
    
    _save_config_yaml_dict(config_data)
    typer.secho(f"Default config file created at '{config.CONFIG_FILE_PATH}'. Please edit it.", fg=typer.colors.GREEN)

@app_cli.command()
def add_static_service(public_hostname: str = typer.Option(...), target_url: str = typer.Option(...)):
    """
    Adds a static service to the config.yml file.
    """
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    new_service_entry = {
        "hostname": public_hostname,
        "target_url": target_url
    }
    cfg_dict['static_services'].append(new_service_entry)
    
    _save_config_yaml_dict(cfg_dict)
    typer.secho(f"Static service '{public_hostname}' -> '{target_url}' added to '{config.CONFIG_FILE_PATH}'.", fg=typer.colors.GREEN)

@app_cli.command()
def bind_static_service(
    public_hostname: str = typer.Option(...),
    container_name_or_id: str = typer.Option(...),
    container_port: int = typer.Option(...)
):
    """
    Binds a static service to a Docker container's hostname and port, automatically updating the target URL.
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_name_or_id)
    except DockerNotFound:
        typer.secho(f"Container '{container_name_or_id}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error connecting to Docker or finding container: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    final_target_url = f"http://{container.name}:{container_port}" # Use container name for internal Docker network
    
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []
    
    # Check if the service already exists
    existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == public_hostname), None)
    if existing_service:
        typer.secho(f"Service '{public_hostname}' already exists: {existing_service['target_url']}.", fg=typer.colors.YELLOW)
        if typer.confirm("Do you want to update the target URL?"):
            existing_service['target_url'] = final_target_url
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