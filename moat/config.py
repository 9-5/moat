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
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML: {e}")
    except Exception as e:
        raise FileNotFoundError(f"Error reading configuration file {CONFIG_FILE_PATH}: {e}")
    
    try:
        validated_settings = MoatSettings(**config_data)
    except Exception as e:
        raise ValueError(f"Error validating configuration: {e}")

    _settings = validated_settings
    _config_last_modified_time = current_mtime
    return _settings

def get_settings() -> MoatSettings:
    if _settings is None:
        raise RuntimeError("Settings not initialized. Ensure load_config() has been called.")
    return _settings

def save_settings(config_content: str) -> bool:
    global _settings, _config_last_modified_time
    try:
        # 1. Validate the new settings first using pydantic
        config_data = yaml.safe_load(config_content)
        validated_settings = MoatSettings(**config_data)
        
        # 2. Write the validated settings back to the config file
        with open(CONFIG_FILE_PATH, 'w') as f:
            yaml.dump(validated_settings.model_dump(), f, indent=2, sort_keys=False)

        print(f"Config: Saved new configuration to {CONFIG_FILE_PATH}")
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