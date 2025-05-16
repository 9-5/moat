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
            config_data = {} # Handle empty YAML file

    validated_settings = MoatSettings(**config_data)
    _settings = validated_settings
    _config_last_modified_time = current_mtime
    return validated_settings

def get_settings() -> MoatSettings:
    global _settings
    if _settings is None:
        # Attempt to load config if it hasn't been loaded yet.
        try:
            _settings = load_config()
        except FileNotFoundError as e:
            print(f"Warning: Configuration file not found: {e}")
        except ValueError as e:
            print(f"Warning: Error loading config: {e}")
    if _settings is None:
        raise RuntimeError("Moat settings not initialized. Ensure config.yml exists and is valid.")
    return _settings

def save_settings(settings: MoatSettings) -> bool:
    global _settings, _config_last_modified_time
    try:
        # First validate the settings by creating a new MoatSettings instance
        validated_settings = MoatSettings(**settings.model_dump())
        
        cfg_dict = validated_settings.model_dump() # Export as dict
        
        print(f"Config: Saving configuration to {CONFIG_FILE_PATH}")
        with open(CONFIG_FILE_PATH, 'w') as f:
            yaml.dump(cfg_dict, f, sort_keys=False, default_flow_style=False)
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