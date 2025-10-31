"""
Configuration management for Peak Load Forecasting Service.
Loads credentials and settings from YAML config file or environment variables.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Centralized configuration management."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config.yaml file. If None, looks for:
                       1. Environment variable CONFIG_PATH
                       2. config/config.yaml in project root
        """
        if config_path is None:
            config_path = os.getenv('CONFIG_PATH')
            if config_path is None:
                # Try to find project root
                project_root = self._find_project_root()
                config_path = project_root / 'config' / 'config.yaml'
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _find_project_root(self) -> Path:
        """Find project root by looking for config directory."""
        current = Path(__file__).resolve().parent
        while current != current.parent:
            if (current / 'config').exists():
                return current
            current = current.parent
        # Fallback to current directory
        return Path.cwd()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file or environment variables."""
        config = {}
        
        # Load from file if it exists
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        
        # Override with environment variables if set
        config = self._apply_env_overrides(config)
        
        return config
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        # Stromme credentials
        if os.getenv('STROMME_BASIC_AUTH_TOKEN'):
            if 'stromme' not in config:
                config['stromme'] = {}
            config['stromme']['basic_auth_token'] = os.getenv('STROMME_BASIC_AUTH_TOKEN')
        
        # Energinet credentials
        if os.getenv('ENERGINET_BEARER_TOKEN'):
            if 'energinet' not in config:
                config['energinet'] = {}
            config['energinet']['bearer_token'] = os.getenv('ENERGINET_BEARER_TOKEN')
        
        # Frost credentials
        if os.getenv('FROST_CLIENT_ID'):
            if 'frost' not in config:
                config['frost'] = {}
            config['frost']['client_id'] = os.getenv('FROST_CLIENT_ID')
            config['frost']['client_secret'] = os.getenv('FROST_CLIENT_SECRET', '')
        
        return config
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path.
        
        Example:
            config.get('stromme.basic_auth_token')
            config.get('data_collection.chunk_size_days', 7)
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    @property
    def stromme_basic_auth_token(self) -> str:
        """Get Stromme Basic Auth token."""
        token = self.get('stromme.basic_auth_token')
        if not token:
            raise ValueError("Stromme basic_auth_token not configured. Set STROMME_BASIC_AUTH_TOKEN env var or config.yaml")
        return token
    
    @property
    def energinet_bearer_token(self) -> str:
        """Get Energinet Bearer token."""
        token = self.get('energinet.bearer_token')
        if not token:
            raise ValueError("Energinet bearer_token not configured. Set ENERGINET_BEARER_TOKEN env var or config.yaml")
        return token
    
    @property
    def frost_client_id(self) -> str:
        """Get Frost API client ID."""
        client_id = self.get('frost.client_id')
        if not client_id:
            raise ValueError("Frost client_id not configured. Set FROST_CLIENT_ID env var or config.yaml")
        return client_id


# Global config instance (lazy initialization)
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

