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
        yaml.dump(config_data, f, sort_keys=False, default_flow_styl
... (FILE CONTENT TRUNCATED) ...
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