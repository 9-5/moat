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
    Initialize a default config.yml if one does not exist.
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
        typer.secho("Default config file created. Edit config.yml to configure.", fg=typer.colors.GREEN)

@app_cli.command()
def add_user(username: str):
    """
    Add a user to the database.
    """
    password = typer.prompt("Enter password for user", hide_input=True)
    password_confirm = typer.prompt("Confirm password", hide_input=True)

    if password != password_confirm:
        typer.secho("Passwords do not match.", fg=typer.colors.RED)
        raise typer.Exit()

    try:
        asyncio.run(database.init_db())
        asyncio.run(database.create_user_db(models.User(username=username), password))
        typer.secho(f"User {username} created successfully.", fg=typer.colors.GREEN)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)

@app_cli.command()
def run():
    """
    Run the Moat server.
    """
    uvicorn.run("moat.server:app", host="0.0.0.0", port=8000, reload=True)

@app_cli.command()
def add_static_service(public_hostname: str, target_url: str):
    """
    Add a static service (reverse proxy entry) to the configuration file.
    """
    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict:
        cfg_dict['static_services'] = []

    # Check if the service already exists.
    for service in cfg_dict['static_services']:
        if service['hostname'] == public_hostname:
            typer.secho(f"A service with hostname '{public_hostname}' already exists.", fg=typer.colors.YELLOW)
            update = typer.confirm("Do you want to update the target URL?")
            if update:
                service['target_url'] = target_url
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
def bind_static_service_to_docker(public_hostname: str, container_name_or_id: str):
    """
    Add a static service, automatically using the container's network.
    """
    try:
        client = docker.from_env()
        try:
            container = client.containers.get(container_name_or_id)
        except DockerNotFound:
            typer.secho(f"Container '{container_name_or_id}' not found.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        container_details = container.attrs
        network_settings = container_details.get('NetworkSettings')
        if not network_settings:
            typer.secho(f"Could not retrieve network settings for container '{container_name_or_id}'.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        # Inspect network to find container's IP.
        # For 'bridge' network, IP address is directly in the container info.
        # For user-defined networks, need to iterate through endpoints config.
        if 'Networks' in network_settings:
            # Iterate through attached networks to find an IP address.
            container_network = None
            container_ip = None
            for network_name, network_config in network_settings['Networks'].items():
                container_network = network_name
                container_ip = network_config['IPAddress']
                if container_ip:
                    break
            if not container_ip:
                typer.secho(f"No IP address found in container's network settings.", fg=typer.colors.RED)
                raise typer.Exit()
            final_target_url = f"http://{container_ip}:{80}" # Default to port 80, can't reliably detect automatically
        else:
            typer.secho(f"Container not connected to any network.", fg=typer.colors.RED)
            raise typer.Exit()

        # Ask if this URL is OK.
        typer.secho(f"Detected target URL: {final_target_url}", fg=typer.colors.BLUE)
        ok = typer.confirm("Is this correct?")
        if not ok:
            final_target_url = typer.prompt("Please enter the correct target URL (e.g., http://127.0.0.1:8080)")

    except Exception as e:
        typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)