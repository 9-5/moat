import yaml
from pathlib import Path
from .models import MoatSettings
import copy
from typing import Optional

CONFIG_FILE_PATH = Path("config.yml")
_settings: Optional[MoatSettings] = None # Renamed to avoid conflict with getter
_config_last_modified_time: Optional[float] = None

def load_config(force_reload: bool = False) -> MoatSettings:
    global _settings, _config_last_modified_time
    
    if not CONFIG_FILE_PATH.exists():
        raise FileNotFoundError(f"Configuration file {CONFIG_FILE_PATH} not found.")

    current_mtime = CONFIG_FILE_PATH.stat().st_mtime
    
    if not force_reload and _settings is not None and _config_last_modified_time == current_mtime:
        return _settings

    print(f"Config: Loading configuration from {CONFIG_FILE_PATH}")
    with open(CONFIG_FILE_PATH, 'r') as f:
        config_data = yaml.safe_load(f)
        if config_data is None:
            config_data = {}

    validated_settings = MoatSettings(**config_data)
    _settings = validated_settings
    _config_last_modified_time = current_mtime
    return _settings

async def get_settings_async() -> MoatSettings:
    """Asynchronous-friendly getter for settings."""
    # This version is needed if settings are loaded during async startup.
    global _settings
    if _settings is None:
        return load_config()
    return _settings

def get_settings() -> MoatSettings:
    """Access Moat settings."""
    global _settings
    if _settings is None:
        return load_config()
    return _settings

def save_settings(config_content: str) -> bool:
    """Saves settings to the configuration file."""
    global _settings, _config_last_modified_time

    try:
        config_data = yaml.safe_load(config_content)

        # Validate the loaded data against the MoatSettings model
        validated_settings = MoatSettings(**config_data)

        # Write the validated data back to the config file
        with open(CONFIG_FILE_PATH, 'w') as f:
            yaml.dump(validated_settings.model_dump(exclude_none=True), f, sort_keys=False) # exclude_none cleans up output

        print(f"Config: Saved new configuration to {CONFIG_FILE_PATH}")
        _settings = validated_settings
        _config_last_modified_time = CONFIG_FILE_PATH.stat().st_mtime
        return True
    except Exception as e:
        print(f"Config: Error validating or saving new settings: {e}")
        return False

def get_current_config_as_dict() -> dict: