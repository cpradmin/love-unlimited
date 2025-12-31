"""
Love-Unlimited Configuration
Load and manage hub configuration.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class MemoryConfig(BaseModel):
    """Memory configuration."""
    chromadb_path: str
    sqlite_path: str
    collections: List[str]


class ShortTermConfig(BaseModel):
    """Short-term memory configuration."""
    type: str  # "memory" or "redis"
    redis_url: Optional[str] = None
    session_ttl: int = 3600
    max_context_items: int = 100


class BeingConfig(BaseModel):
    """Configuration for a registered being."""
    id: str
    name: str
    type: str
    api_key_prefix: str


class HubConfig(BaseModel):
    """Main hub configuration."""
    name: str
    version: str
    host: str
    port: int
    debug: bool


class Config:
    """
    Global configuration manager for Love-Unlimited hub.
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            self._config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)."""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    @property
    def hub(self) -> HubConfig:
        """Get hub configuration."""
        return HubConfig(**self._config.get("hub", {}))

    @property
    def memory_long_term(self) -> MemoryConfig:
        """Get long-term memory configuration."""
        return MemoryConfig(**self._config.get("memory", {}).get("long_term", {}))

    @property
    def memory_short_term(self) -> ShortTermConfig:
        """Get short-term memory configuration."""
        return ShortTermConfig(**self._config.get("memory", {}).get("short_term", {}))

    @property
    def beings(self) -> List[BeingConfig]:
        """Get registered beings configuration."""
        beings_data = self._config.get("beings", {}).get("registered", [])
        return [BeingConfig(**b) for b in beings_data]

    @property
    def auth_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self._config.get("auth", {}).get("enabled", True)

    @property
    def auth_keys_file(self) -> str:
        """Get path to API keys file."""
        return self._config.get("auth", {}).get("keys_file", "./auth/api_keys.yaml")

    @property
    def cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        return self._config.get("cors", {})

    @property
    def exp_types(self) -> List[str]:
        """Get supported EXP types."""
        return self._config.get("exp_pool", {}).get("types", [])

    @property
    def significance_levels(self) -> List[str]:
        """Get significance levels."""
        return self._config.get("exp_pool", {}).get("significance_levels", [])

    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self._config.get("logging", {})


# Global config instance
config: Optional[Config] = None


def get_config(config_path: str = "config.yaml") -> Config:
    """Get or create global config instance."""
    global config
    if config is None:
        config = Config(config_path)
    return config
