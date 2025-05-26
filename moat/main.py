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
    host: str = typer.Option("0.0.0.0", help="Host IP to listen on."),
    port: int = typer.Option(8000, help="Port to listen on.")
):
    """
    Run the Moat server.
    """
    uvicorn.run("moat.server:app", host=host, port=port, reload=True)

@app_cli.command()
def init_config():
    """
    Initialize a default config.yml file if one doesn't exist.
    """
    if not config.CONFIG_FILE_PATH.exists():
        default_config = {
            "listen_host": "0.0.0.0",
            "listen_port": 8000,
            "secret_key": "PLEASE_CHANGE_ME",
            "access_token_expire_minutes": 60,
            "database_url": "sqlite+aiosqlite:///./moat.db",
            "moat_base_url": None,
            "cookie_domain": None,
            "docker_monitor_enabled": True,
            "moat_label_prefix": "moat",
            "static_services": []
        }
        _save_config_yaml_dict(default_config)
        typer.secho("Default config.yml created.  Please review and customize!", fg=typer.colors.GREEN)
    else:
        typer.secho("config.yml already exists.", fg=typer.colors.YELLOW)

@app_cli.command()
def create_user(username: str = typer.Option(..., prompt="Username"), password: str = typer.Option(..., prompt="Password", hide_input=True, confirmation_prompt=True)):
    """
    Create a new user.
    """
    asyncio.run(_async_create_user(username, password))

async def _async_create_user(username: str, password: str):
    try:
        await database.init_db() # Ensure DB exists before creating user
        user = models.User(username=username)
        await database.create_user_db(user, password)
        typer.secho(f"User {username} created successfully.", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)

@app_cli.command()
def add_static_service(
    public_hostname: str = typer.Option(..., help="The public hostname for the service (e.g., app.example.com)."),
    target_url: str = typer.Option(..., help="The target URL for the service (e.g., http://localhost:3000)."),
):
    """
    Add a static service entry to the config.yml file.
    """
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    #Check if service already exists, prompt to overwrite
    existing_service = next((s for s in cfg_dict['static_services'] if s.get('hostname') == public_hostname), None)
    if existing_service:
        if typer.confirm(f"Service '{public_hostname}' already exists. Overwrite?", default=False):
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
def bind_static_service(
    container_name: str = typer.Option(..., help="The name of the Docker container."),
    public_hostname: str = typer.Option(..., help="The public hostname for the service (e.g., app.example.com)."),
    container_port: int = typer.Option(..., help="The port exposed by the Docker container.")
):
    """
    Binds a static service entry to a Docker container's port, auto-generating the target URL.
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
    except docker.errors.NotFound:
        typer.secho(f"Container '{container_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    final_target_url = f"http://{container_name}:{container_port}"

    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Check if service already exists, prompt to overwrite.
    existing_service = next((s for s in cfg_dict['static_services'] if s.get('hostname') == public_hostname), None)
    if existing_service:
        if typer.confirm(f"Service '{public_hostname}' already exists. Update target to '{final_target_url}' (bound to container {container.name})?", default=False):
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
    typer.secho(f"Static service '{public_hostname}' -> '{final_target_url}' added for container '{container.name}'.", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app_cli()