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
            if config_data is None:
                config_data = {}  # Treat empty file as empty dict
            validated_settings = MoatSettings(**config_data)
            _settings = validated_settings
            _config_last_modified_time = current_mtime
            return _settings
    except FileNotFoundError:
        raise 
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML in {CONFIG_FILE_PATH}: {e}")
    except Exception as e:
        raise ValueError(f"Error loading configuration from {CONFIG_FILE_PATH}: {e}")

def get_settings() -> MoatSettings:
    """
    Returns the current configuration settings.  Loads from file if not already loaded, or if the file has been modified.
    """
    if _settings is None:
        return load_config()
    else:
        try:
            # Attempt to reload config if file has been modified
            current_mtime = CONFIG_FILE_PATH.stat().st_mtime
            if _config_last_modified_time != current_mtime:
                print("Config: Configuration file has changed, reloading...")
                return load_config(force_reload=True)
            return _settings
        except FileNotFoundError:
            print("Warning: Configuration file not found.  Returning cached settings (may be outdated).")
            return _settings # Return cached, even if outdated, to avoid crash

def save_settings(config_content: str) -> bool:
    """Saves the provided configuration content to the config file.  Returns True on success, False on failure."""
    global _settings, _config_last_modified_time
    
    try:
        #Load config to check for errors:
        cfg_dict = yaml.safe_load(config_content)
        if cfg_dict is None:
            cfg_dict = {}
        validated_settings = MoatSettings(**cfg_dict)

        with open(CONFIG_FILE_PATH, 'w') as f:
            yaml.dump(validated_settings.model_dump(), f, sort_keys=False) # Persist all fields
        print(f"Config: Saved new settings to {CONFIG_FILE_PATH}")
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