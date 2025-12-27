"""
Configuration Manager for Urban Traffic System
"""
import json
import os
from typing import Dict, Any
from pathlib import Path
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ConfigManager:
    """Manages configuration files for the system."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.configs = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files."""
        config_files = [
            "sri_lanka_locations.json",
            "thresholds.json",
            "api_config.json"
        ]
        
        for config_file in config_files:
            filepath = self.config_dir / config_file
            try:
                if filepath.exists():
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.configs[config_file] = json.load(f)
                    logger.info(f"Loaded config: {config_file}")
                else:
                    logger.warning(f"Config file not found: {config_file}")
                    self.configs[config_file] = self._get_default_config(config_file)
            except Exception as e:
                logger.error(f"Error loading {config_file}: {e}")
                self.configs[config_file] = self._get_default_config(config_file)
    
    def _get_default_config(self, config_file: str) -> Dict[str, Any]:
        """Get default configuration for missing files."""
        defaults = {
            "sri_lanka_locations.json": {
                "major_cities": {
                    "Colombo": {
                        "latitude": 6.9271,
                        "longitude": 79.8612,
                        "center": "Colombo Fort"
                    }
                }
            },
            "thresholds.json": {
                "traffic_levels": {
                    "light": {"max_delay": 5},
                    "moderate": {"max_delay": 15},
                    "heavy": {"max_delay": 30},
                    "severe": {"max_delay": 999}
                }
            },
            "api_config.json": {
                "google_maps": {
                    "max_alternatives": 3,
                    "timeout_seconds": 30
                }
            }
        }
        return defaults.get(config_file, {})
    
    def get_config(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """Get configuration value."""
        config = self.configs.get(config_name, {})
        
        if key is None:
            return config
        
        # Support nested keys with dot notation
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        
        return value if value is not None else default
    
    def update_config(self, config_name: str, updates: Dict[str, Any]):
        """Update configuration values."""
        if config_name not in self.configs:
            self.configs[config_name] = {}
        
        self._update_dict(self.configs[config_name], updates)
        
        # Save to file
        filepath = self.config_dir / config_name
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.configs[config_name], f, indent=2)
            logger.info(f"Updated config: {config_name}")
        except Exception as e:
            logger.error(f"Error saving config {config_name}: {e}")
    
    def _update_dict(self, target: Dict, updates: Dict):
        """Recursively update dictionary."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._update_dict(target[key], value)
            else:
                target[key] = value
    
    def get_traffic_thresholds(self) -> Dict[str, Any]:
        """Get traffic threshold configuration."""
        return self.get_config("thresholds.json", "traffic_levels", {})
    
    def get_sri_lanka_cities(self) -> Dict[str, Any]:
        """Get Sri Lanka cities configuration."""
        return self.get_config("sri_lanka_locations.json", "major_cities", {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration."""
        return self.get_config("api_config.json", "google_maps", {})