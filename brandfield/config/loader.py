"""Discovers and loads client YAML configuration files."""

import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from brandfield.config.schema import ClientConfig

CLIENTS_DIR = Path(__file__).parent.parent.parent / "clients"


class ConfigError(Exception):
    """Raised when a client config file is invalid."""


def load_client_config(path: Path) -> ClientConfig:
    """Load and validate a single client YAML file."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ConfigError(f"Config file is empty: {path}")

    try:
        return ClientConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(
            f"Invalid config in {path.name}:\n{e}"
        ) from e


def load_all_clients(clients_dir: Path = CLIENTS_DIR) -> list[ClientConfig]:
    """Discover and load all client YAML files (skips _template.yml)."""
    if not clients_dir.exists():
        return []

    configs = []
    for path in sorted(clients_dir.glob("*.yml")):
        if path.stem.startswith("_"):
            continue
        configs.append(load_client_config(path))

    return configs


def load_credentials(client: ClientConfig) -> dict:
    """Resolve API credentials from environment variables."""
    token_env = client.meta.access_token_env
    token = os.environ.get(token_env)
    return {"access_token": token, "token_env": token_env}


def validate_credentials(client: ClientConfig, dry_run: bool = False) -> None:
    """Raise ConfigError if required credentials are missing (unless dry_run)."""
    if dry_run:
        return

    creds = load_credentials(client)
    if not creds["access_token"]:
        raise ConfigError(
            f"Missing environment variable '{creds['token_env']}' for client "
            f"'{client.slug}'. Set it or use --dry-run to skip credential checks."
        )
