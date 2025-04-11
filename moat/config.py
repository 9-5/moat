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
                config_data = {}  # Treat empty files as empty dictionaries
            _settings = MoatSettings(**config_data)
            _config_last_modified_time = current_mtime
            return _settings
    except Exception as e:
        print(f"Config: Error loading configuration: {e}")
        raise

def get_settings() -> MoatSettings:
    if _settings is None:
        raise RuntimeError("Settings not initialized. Ensure load_config has been called.")
    return _settings

def save_settings(validated_settings: MoatSettings) -> bool:
    global _settings, _config_last_modified_time
    try:
        # Convert Pydantic model back to a dictionary for YAML serialization.  Use exclude_unset
        # to only save values that were explicitly set, keeping the config file cleaner.
        config_data = validated_settings.model_dump(exclude_unset=True)

        with open(CONFIG_FILE_PATH, 'w') as f:
            yaml.dump(config_data, f, sort_keys=False, default_flow_style=False) # Preserve order

        print(f"Config: Saved configuration to {CONFIG_FILE_PATH}")
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