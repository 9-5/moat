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
    typer.secho(f"Configuration updated in {config.CONFIG_FILE_PATH}", fg=typer.colors.CYAN)
    typer.secho("If Moat server is running, it should hot-reload relevant settings soon.", fg=typer.colors.YELLOW)


@app_cli.command()
def run(
    host: str = typer.Option(None, help="Host to bind the server to. Overrides config."),
    port: int = typer.Option(None, help="Port to bind the server to. Overrides config."),
    reload: bool = typer.Option(False, "--reload", help="Enable uvicorn auto-reload (for development of Moat code itself).")
):
    """Run the Moat server. Hot-reloads config.yml changes for some settings."""
    try:
        if not config.CONFIG_FILE_PATH.exists():
             typer.secho(f"Error: Moat configuration file '{config.CONFIG_FILE_PATH}' not found.", fg=typer.colors.RED)
             typer.secho("Try running `moat init-config` first.", fg=typer.colors.YELLOW)
             raise typer.Exit(code=1)
        
        cfg_for_run = config.get_settings()

    except RuntimeError as e: 
        typer.secho(f"Error loading Moat configuration: {e}", fg=typer.colors.RED)
        typer.secho("Ensure 'config.yml' is valid or try `moat init-config`.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
        
    final_host = host if host is not None else cfg_for_run.listen_host
    final_port = port if port is not None else cfg_for_run.listen_port
    
    uvicorn.run(
        "moat.server:app",
        host=final_host,
        port=final_port,
        reload=reload, 
        forwarded_allow_ips='*'
    )

@app_cli.command()
def add_user(
    username: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, confirmation_prompt=True, hide_input=True)
):
    """Add a new user to the Moat database."""
    try:
        config.get_settings() 
    except (RuntimeError, FileNotFoundError) as e:
        typer.secho(f"Error: Moat configuration (config.yml) not found or improperly loaded: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    async def _add_user():
        await database.init_db() 
        try:
            user_in_db = await database.create_user_db(models.User(username=username), password)
            typer.secho(f"User '{user_in_db.username}' added successfully.", fg=typer.colors.GREEN)
        except ValueError as e: 
            typer.secho(f"Error: {e}", fg=typer.colors.RED)
        except Exception as e:
            typer.secho(f"An unexpected error occurred: {e}", fg=typer.colors.RED)

    asyncio.run(_add_user())

@app_cli.command()
def init_config(force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config.yml.")):
    """Initialize a sample config.yml in the current directory."""
    config_path = Path("config.yml")
    if config_path.exists() and not force:
        typer.secho(f"{config_path} already exists. Use --force to overwrite.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    default_config_content = f"""
listen_host: "0.0.0.0"
listen_port: 8000
secret_key: "YOUR_VERY_SECRET_KEY_CHANGE_THIS_NOW_PLEASE" # Generate with: openssl rand -hex 32
access_token_expire_minutes: 60
database_url: "sqlite+aiosqlite:///./moat.db"

# Public base URL for Moat's auth pages (e.g., "https://moat.yourdomain.com")
# Required if Moat itself is behind a reverse proxy or tunnel on a different URL than it listens on.
moat_base_url: null

# Cookie domain for SSO (e.g., ".yourdomain.com" or a specific hostname)
# Ensure this matches how your applications are accessed.
cookie_domain: null

# Docker label monitoring settings
docker_monitor_enabled: true
moat_label_prefix: "moat" # e.g., moat.enable, moat.hostname

# Static service definitions (useful for non-Docker services or fixed targets)
static_services:
#  - hostname: "service1.localhost"
#    target_url: "http://127.0.0.1:9001"
#  - hostname: "another.example.com"
#    target_url: "http://192.168.1.100:8080"
"""
    with open(config_path, "w") as f:
        f.write(default_config_content)
    typer.secho(f"Sample {config_path} created. Please edit it, especially the secret_key!", fg=typer.colors.GREEN)
    typer.secho("If Moat is behind a proxy (like Cloudflare Tunnel), set 'moat_base_url' to its public HTTPS URL.", fg=typer.colors.YELLOW)
    typer.secho("Set 'cookie_domain' appropriately if you want SSO across subdomains (e.g., '.yourdomain.com').", fg=typer.colors.YELLOW)


@app_cli.command("config:add-static")
def add_static_service(
    hostname: str = typer.Option(..., prompt="Hostname Moat will listen for (e.g., app.mydomain.com)"),
    target_url: str = typer.Option(..., prompt="Target URL for the backend service (e.g., http://localhost:3000 or http://container_name:port)")
):
    """Adds a new static service definition to config.yml."""
    if not config.CONFIG_FILE_PATH.exists():
        typer.secho(f"Error: {config.CONFIG_FILE_PATH} not found. Run `moat init-config` first.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        if not (target_url.startswith("http://") or target_url.startswith("https://")):
            raise ValueError("Target URL must start with http:// or https://")
        if "://" in hostname or "/" in hostname: # Basic check
            raise ValueError("Hostname should be a simple domain name (e.g., app.example.com) without scheme or path.")
    except ValueError as e:
        typer.secho(f"Invalid input: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    cfg_dict = _load_config_yaml_dict()
    
    if 'static_services' not in cfg_dict or cfg_dict['static_services'] is None: # Ensure list exists
        cfg_dict['static_services'] = []
    
    existing_service_index = -1
    for i, service in enumerate(cfg_dict['static_services']):
        if service.get('hostname') == hostname:
            existing_service_index = i
            break
            
    if existing_service_index != -1:
        typer.secho(f"Static service for hostname '{hostname}' already exists with target '{cfg_dict['static_services'][existing_service_index].get('target_url')}'.", fg=typer.colors.YELLOW)
        if typer.confirm(f"Do you want to update its target_url to '{target_url}'?"):
            cfg_dict['static_services'][existing_service_index]['target_url'] = target_url
            _save_config_yaml_dict(cfg_dict)
            typer.secho(f"Static service '{hostname}' updated.", fg=typer.colors.GREEN)
        else:
            typer.secho("Operation cancelled.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    new_service = {"hostname": hostname, "target_url": target_url}
    cfg_dict['static_services'].append(new_service)
    
    _save_config_yaml_dict(cfg_dict)
    typer.secho(f"Static service '{hostname}' -> '{target_url}' added to {config.CONFIG_FILE_PATH}.", fg=typer.colors.GREEN)


@app_cli.command("docker:bind")
def docker_bind_container(
    container_name_or_id: str = typer.Argument(..., help="Name or ID of the running Docker container."),
    public_hostname: str = typer.Option(..., prompt="Public hostname for this service (e.g., myapp.moat.bor.i.ng)"),
    target_port_override: Optional[int] = typer.Option(None, help="Specify container's internal port if multiple exposed or auto-detection fails."),
    target_scheme: str = typer.Option("http", help="Scheme for the target service (http or https).")
):
    """
    Binds a running Docker container to a public hostname by adding it as a static service
    to config.yml. Moat will then proxy requests for that hostname to the container.
    This command creates a static entry in config.yml, not using dynamic Docker labels.
    """
    if not config.CONFIG_FILE_PATH.exists():
        typer.secho(f"Error: {config.CONFIG_FILE_PATH} not found. Run `moat init-config` first.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        client = docker.from_env()
        container = client.containers.get(container_name_or_id)
    except DockerNotFound:
        typer.secho(f"Error: Docker container '{container_name_or_id}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except docker.errors.DockerException as e:
        typer.secho(f"Error connecting to Docker: {e}. Is Docker running and accessible?", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if container.status != "running":
        typer.secho(f"Error: Container '{container.name}' is not running (status: {container.status}).", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    container_internal_port_to_target = None
    if target_port_override:
        container_internal_port_to_target = target_port_override
    else:
        exposed_ports_config = container.attrs['Config'].get('ExposedPorts', {}) # e.g. {"80/tcp": {}}
        if not exposed_ports_config:
            typer.secho(f"Error: Container '{container.name}' has no exposed ports in its image config.", fg=typer.colors.RED)
            typer.secho("Use --target-port-override or ensure the Docker image EXPOSEs a port.", fg=typer.colors.YELLOW)
            raise typer.Exit(code=1)

        preferred_ports_order = ["80/tcp", "8080/tcp", "3000/tcp", "5000/tcp", "8000/tcp"]
        for p_port_str in preferred_ports_order:
            if p_port_str in exposed_ports_config:
                container_internal_port_to_target = int(p_port_str.split('/')[0])
                break
        
        if not container_internal_port_to_target:
            first_exposed_key = list(exposed_ports_config.keys())[0]
            container_internal_port_to_target = int(first_exposed_key.split('/')[0])
            typer.secho(f"Warning: Multiple/non-standard ports exposed. Auto-selected internal container port: {container_internal_port_to_target}. "
                        f"Verify or use --target-port-override.", fg=typer.colors.YELLOW)

    if not container_internal_port_to_target:
        typer.secho("Error: Could not determine an internal container port to target.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    internal_port_tcp_str = f"{container_internal_port_to_target}/tcp"
    port_mappings = container.attrs['NetworkSettings']['Ports'].get(internal_port_tcp_str) # More reliable for published ports

    target_host_for_url: str
    target_port_for_url: int

    if port_mappings and isinstance(port_mappings, list) and len(port_mappings) > 0:
        host_port_str = port_mappings[0].get('HostPort') # Take the first one
        for mapping in port_mappings: # Prefer 127.0.0.1 if explicitly bound
            if mapping.get('HostIp') == '127.0.0.1':
                host_port_str = mapping.get('HostPort')
                break
        
        if not host_port_str:
             typer.secho(f"Error: Could not determine published host port for container port {internal_port_tcp_str}.", fg=typer.colors.RED)
             raise typer.Exit(code=1)

        target_host_for_url = "127.0.0.1"
        target_port_for_url = int(host_port_str)
        typer.secho(f"Info: Container '{container.name}' port {internal_port_tcp_str} is published to host as {target_host_for_url}:{target_port_for_url}.", fg=typer.colors.BLUE)
    else:
        # Port is exposed but not published. Target by container name.
        target_host_for_url = container.name
        target_port_for_url = container_internal_port_to_target
        typer.secho(f"Info: Container '{container.name}' port {internal_port_tcp_str} is exposed. "
                    f"Targeting by container name: '{target_host_for_url}:{target_port_for_url}'. "
                    "This requires Moat and the container to be on a shared Docker network for resolution.", fg=typer.colors.BLUE)

    final_target_url = f"{target_scheme}://{target_host_for_url}:{target_port_for_url}"
    
    typer.secho(f"Proposed static service: Hostname '{public_hostname}' -> Target '{final_target_url}' (for container '{container.name}')", fg=typer.colors.CYAN)

    cfg_dict = _load_config_yaml_dict()
    if 'static_services' not in cfg_dict or cfg_dict['static_services'] is None:
        cfg_dict['static_services'] = []

    existing_service_idx = -1
    for i, service in enumerate(cfg_dict['static_services']):
        if service.get('hostname') == public_hostname:
            existing_service_idx = i
            break
            
    if existing_service_idx != -1:
        typer.secho(f"Static service for hostname '{public_hostname}' already exists (target: {cfg_dict['static_services'][existing_service_idx].get('target_url')}).", fg=typer.colors.YELLOW)
        if typer.confirm(f"Update its target_url to '{final_target_url}'?"):
            cfg_dict['static_services'][existing_service_idx]['target_url'] = final_target_url
            cfg_dict['static_services'][existing_service_idx]['_comment'] = f"Bound to Docker container: {container.name} (ID: {container.short_id}) via docker:bind"
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
