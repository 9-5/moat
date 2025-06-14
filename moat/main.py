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
    typer.secho(f"Default config created at {config.CONFIG_FILE_PATH}", fg=typer.colors.GREEN)

@app_cli.command()
def add_user(username: str):
    """
    Add a new user to the database.
    """
    import getpass
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if password != password_confirm:
        typer.secho("Passwords do not match.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    async def _create_user():
        await database.init_db()
        try:
            user_data = models.User(username=username)
            await database.create_user_db(user_data, password)
            typer.secho(f"User '{username}' created successfully.", fg=typer.colors.GREEN)
        except ValueError as e:
            typer.secho(str(e), fg=typer.colors.RED)
        except Exception as e:
            typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)

    asyncio.run(_create_user())

@app_cli.command()
def run(
    reload: bool = typer.Option(False, help="Enable auto-reload on code changes (development only).")
):
    """
    Run the Moat server.
    """
    uvicorn.run("moat.server:app", host=config.get_settings().listen_host, port=config.get_settings().listen_port, reload=reload)

@app_cli.command()
def add_static(
    public_hostname: str = typer.Option(..., help="The public hostname for the service (e.g., app.example.com)."),
    target_url: str = typer.Option(..., help="The target URL for the service (e.g., http://127.0.0.1:8000)."),
):
    """
    Add a static service to the configuration.
    """
    cfg_dict = _load_config_yaml_dict()
    if not cfg_dict.get('static_services'):
        cfg_dict['static_services'] = []

    # Basic validation of the URL
    try:
        from urllib.parse import urlparse
        result = urlparse(target_url)
        if not all([result.scheme, result.netloc]):
            typer.secho("Invalid target URL. Ensure it includes scheme (http/https) and netloc (host:port).", fg=typer.colors.RED)
            raise typer.Exit()
    except:
        typer.secho("Invalid target URL format.", fg=typer.colors.RED)
        raise typer.Exit()
    
    new_service_entry = {
        "hostname": public_hostname,
        "target_url": target_url
    }
    cfg_dict['static_services'].append(new_service_entry)
    _save_config_yaml_dict(cfg_dict)
    typer.secho(f"Static service '{public_hostname}' -> '{target_url}' added.", fg=typer.colors.GREEN)

@app_cli.command()
def bind_docker(
    public_hostname: str = typer.Option(..., help="The public hostname for the service (e.g., app.example.com)."),
    container_name_or_id: str = typer.Option(..., help="The Docker container name or ID."),
    target_port: int = typer.Option(..., help="The target port on the Docker container."),
    ):
    """
    Bind a public hostname to a Docker container, creating a static service entry with a comment.
    """

    client = docker.from_env()
    try:
        container = client.containers.get(container_name_or_id)
    except DockerNotFound:
        typer.secho(f"Container '{container_name_or_id}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error connecting to Docker: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    final_target_url = f"http://{container.name}:{target_port}" # Container name works inside docker network
    
    cfg_dict = _load_config_yaml_dict()
    if not cfg_dict.get('static_services'):
        cfg_dict['static_services'] = []
    
    # Check if the service already exists and prompt to update
    existing_service = next((s for s in cfg_dict['static_services'] if s.get('hostname') == public_hostname), None)
    if existing_service:
        if typer.confirm(f"Service '{public_hostname}' already exists. Update target URL to '{final_target_url}'?"):
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