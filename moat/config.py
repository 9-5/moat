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
                config_data = {} # Treat empty file as empty dict
            _settings = MoatSettings(**config_data)
            _config_last_modified_time = current_mtime
            return _settings
    except FileNotFoundError:
        print(f"Config: Configuration file not found at {CONFIG_FILE_PATH}")
        raise
    except yaml.YAMLError as e:
        print(f"Config: YAML error parsing {CONFIG_FILE_PATH}: {e}")
        raise ValueError(f"Invalid YAML format in {CONFIG_FILE_PATH}") from e
    except ValueError as e:
        print(f"Config: Validation error loading settings: {e}")
        raise

async def save_settings(validated_settings: MoatSettings) -> bool:
    """Saves settings to the configuration file."""
    global _settings, _config_last_modified_time

    try:
        # Convert Pydantic model back to a dictionary for YAML serialization
        cfg_dict = validated_settings.model_dump()
        
        # Write to file
        with open(CONFIG_FILE_PATH, 'w') as f:
            yaml.dump(cfg_dict, f, sort_keys=False)  # sort_keys=False keeps the order from the model
        print(f"Config: New settings saved to {CONFIG_FILE_PATH}")
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