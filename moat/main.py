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
    Initialize a default config.yml file if one does not exist.
    """
    if config.CONFIG_FILE_PATH.exists():
        typer.secho("Config file already exists. Doing nothing.", fg=typer.colors.YELLOW)
    else:
        default_config = {
            'listen_host': "0.0.0.0",
            'listen_port': 8000,
            'secret_key': "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE", # Generate with: openssl rand -hex 32
            'access_token_expire_minutes': 60,
            'database_url': "sqlite+aiosqlite:///./moat.db",
            'moat_base_url': None,
            'cookie_domain': None,
            'docker_monitor_enabled': True,
            'moat_label_prefix': "moat",
            'static_services': []
        }
        _save_config_yaml_dict(default_config)
        typer.secho("Default config file created. Please edit it.", fg=typer.colors.GREEN)

@app_cli.command()
def run(
    reload: bool = typer.Option(False, help="Enable auto-reload for development.")
):
    """
    Run the Moat server.
    """
    config.load_config(force_reload=True) # Load config on run
    typer.secho("Starting Moat...", fg=typer.colors.GREEN)
    uvicorn.run("moat.server:app", host=config.get_settings().listen_host, port=config.get_settings().listen_port, reload=reload)

@app_cli.command()
def create_user(username: str = typer.Option(...), password: str = typer.Option(...)):
    """
    Create a new user.
    """
    async def _create_user(username, password):
        try:
            await database.init_db()
            user = models.User(username=username)
            await database.create_user_db(user, password)
            typer.secho(f"User '{username}' created successfully.", fg=typer.colors.GREEN)
        except ValueError as e:
            typer.secho(str(e), fg=typer.colors.RED)
        except Exception as e:
            typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)

    asyncio.run(_create_user(username, password))

@app_cli.command()
def add_static_service(
    hostname: str = typer.Option(...),
    target_url: str = typer.Option(...)
):
    """
    Add a static service to the configuration.
    """
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    new_service_entry = {
        "hostname": hostname,
        "target_url": target_url
    }
    cfg_dict['static_services'].append(new_service_entry)
    _save_config_yaml_dict(cfg_dict)
    typer.secho(f"Static service '{hostname}' -> '{target_url}' added.", fg=typer.colors.GREEN)

@app_cli.command()
def remove_static_service(hostname: str = typer.Option(...)):
    """
    Remove a static service from the configuration.
    """
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        typer.secho("No static services configured.", fg=typer.colors.YELLOW)
        return

    existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == hostname), None)

    if existing_service:
        cfg_dict['static_services'].remove(existing_service)
        _save_config_yaml_dict(cfg_dict)
        typer.secho(f"Static service '{hostname}' removed.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Static service '{hostname}' not found.", fg=typer.colors.YELLOW)

@app_cli.command()
def docker_bind(
    container_name: str = typer.Option(...),
    public_hostname: str = typer.Option(...)
):
    """
    Binds a Docker container to a public hostname by adding a static service entry
    based on container labels.
    """
    docker_client = docker.from_env()
    try:
        container = docker_client.containers.get(container_name)
    except DockerNotFound:
        typer.secho(f"Container '{container_name}' not found.", fg=typer.colors.RED)
        raise typer.Exit()

    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Build target URL: first check `moat.target_url` label, otherwise default to container name:port
    moat_label_prefix = cfg_dict.get('moat_label_prefix', 'moat')
    target_url_label = f"{moat_label_prefix}.target_url"
    final_target_url = container.labels.get(target_url_label)

    if not final_target_url: # No explicit override
        # inspect "exposed ports" to get the port
        container_ports = container.attrs['NetworkSettings']['Ports']
        exposed_ports = [k.split('/')[0] for k in container_ports.keys()] # drop "/tcp" etc
        if not exposed_ports:
            typer.secho(f"Container '{container.name}' does not expose any ports and no {target_url_label} specified.", fg=typer.colors.RED)
            raise typer.Exit()
        if len(exposed_ports) > 1:
             typer.secho(f"Container '{container.name}' exposes multiple ports. Please define the {target_url_label} label to specify which port should be used.", fg=typer.colors.RED)
             raise typer.Exit()

        final_target_url = f"http://{container.name}:{exposed_ports[0]}"
        typer.secho(f"Using default target URL: {final_target_url}", fg=typer.colors.YELLOW)
    else:
        typer.secho(f"Using target URL from label '{target_url_label}': {final_target_url}", fg=typer.colors.GREEN)

    # Check if public_hostname already exists and prompt for overwrite, unless forced
    existing_service = next((s for s in cfg_dict['static_services'] if s['hostname'] == public_hostname), None)

    if existing_service:
        if typer.confirm(f"Static service '{public_hostname}' already exists. Overwrite?", default=False):

            # Need to do this to avoid "remove while iterating" errors.
            index_to_remove = None
            for i, service in enumerate(cfg_dict['static_services']):
              if service['hostname'] == public_hostname:
                index_to_remove = i
                break # exit the loop

            if index_to_remove is not None:
              del cfg_dict['static_services'][index_to_remove]  # Remove old entry
            else:
                typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
                raise typer.Exit()
            break # exit the loop - ensures only one overwrite

    # Inspect container labels for port
    moat_label_prefix = cfg_dict.get('moat_label_prefix', 'moat')
    port_label = f"{moat_label_prefix}.port"
    exposed_port = container.labels.get(port_