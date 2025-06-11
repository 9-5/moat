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

    try:
        validated_settings = MoatSettings(**config_data)
    except Exception as e:
        print(f"Config: Error validating configuration: {e}")
        raise # Re-raise to prevent Moat from running with invalid settings

    _settings = validated_settings
    _config_last_modified_time = CONFIG_FILE_PATH.stat().st_mtime
    return _settings

def save_settings(settings: MoatSettings) -> bool:
    global _settings, _config_last_modified_time
    try:
        cfg_dict = settings.model_dump() # Use model_dump instead of dict()
        
        with open(CONFIG_FILE_PATH, 'w') as f:
            print(f"Config: Saving configuration to {CONFIG_FILE_PATH}")
        
            yaml.dump(cfg_dict, f, sort_keys=False)  # Preserve order
            validated_settings = MoatSettings(**cfg_dict) # re-validate to be 100% sure after saving/loading, but also catch possible serialization errors with pydantic types during save.

            print(f"Config: Successfully saved and validated settings in {CONFIG_FILE_PATH}")
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