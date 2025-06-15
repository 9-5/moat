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

    print(f"Config: Loading configuration from {CONFIG_FILE_PATH} (force_reload: {force_reload}, mtime changed: {_config_last_modified_time != current_mtime})")
    with open(CONFIG_FILE_PATH, 'r') as f:
        config_data = yaml.safe_load(f)
        if config_data is None:
            config_data = {} 
            
    try:
        new_settings = MoatSettings(**config_data)
    except Exception as e:
        print(f"Config: Error parsing new configuration: {e}")
        if _settings is not None: 
            print("Config: Reverting to previously loaded valid configuration due to parsing error.")
            return _settings
        else: 
            raise ValueError(f"Config: Critical error parsing initial configuration: {e}")

    _settings = new_settings
    _config_last_modified_time = current_mtime
    print(f"Config: Successfully loaded/reloaded. Docker Monitor: {_settings.docker_monitor_enabled}, Static Services: {len(_settings.static_services)}")
    return _settings


def get_settings() -> MoatSettings:
    global _settings
    if _settings is None:
        try:
            return load_config()
        except FileNotFoundError:
            raise RuntimeError("Settings not loaded. Ensure config.yml exists or load_config() is called.")
        except ValueError as e: # Catch parsing errors from initial load
             raise RuntimeError(f"Critical error loading initial settings: {e}")
    return _settings

def save_settings(new_settings_data: dict) -> bool:
    """Validates and saves new settings data to config.yml."""
    global _settings, _config_last_modified_time
    try:
        validated_settings = MoatSettings(**new_settings_data)
        
        temp_config_path = CONFIG_FILE_PATH.with_suffix(".yml.tmp")
        with open(temp_config_path, 'w') as f:
            yaml.dump(new_settings_data, f, sort_keys=False, default_flow_style=False)
        temp_config_path.rename(CONFIG_FILE_PATH)
        
        print(f"Config: Settings successfully written to {CONFIG_FILE_PATH}")
        _settings = validated_settings
        _config_last_modified_time = CONFIG_FILE_PATH.stat().st_mtime
        return True
    except Exception as e:
        print(f"Config: Error validating or saving new settings: {e}")
        return False

def get_current_config_as_dict() -> dict:
    """Loads config from file and returns as dict, useful for editing."""
    if CONFIG_FILE_PATH.exists():
        with open(CONFIG_FILE_PATH, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}

try:
    _settings = load_config()
except (FileNotFoundError, ValueError) as e: # Catch parsing errors too
    print(f"Warning: Initial config load failed ({e}). Moat may not function correctly until configured.")
    _settings = None
