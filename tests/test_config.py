"""Tests for config loading and validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from brandfield.config.loader import ConfigError, load_client_config
from brandfield.config.schema import ClientConfig


VALID_CONFIG = {
    "slug": "test_client",
    "display_name": "Test Client",
    "meta": {
        "ad_account_id": "act_123",
        "instagram_business_id": "17841400000000",
        "access_token_env": "META_TOKEN_TEST",
    },
}


def write_yaml(path: Path, data: dict) -> None:
    with path.open("w") as f:
        yaml.dump(data, f)


def test_load_valid_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.yml"
        write_yaml(path, VALID_CONFIG)
        client = load_client_config(path)
        assert isinstance(client, ClientConfig)
        assert client.slug == "test_client"


def test_load_invalid_slug_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "bad.yml"
        bad = {**VALID_CONFIG, "slug": "Has Spaces!"}
        write_yaml(path, bad)
        with pytest.raises(ConfigError, match="Invalid config"):
            load_client_config(path)


def test_load_missing_file_raises():
    with pytest.raises(ConfigError, match="not found"):
        load_client_config(Path("/nonexistent/path.yml"))


def test_defaults_are_applied():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "minimal.yml"
        write_yaml(path, VALID_CONFIG)
        client = load_client_config(path)
        assert client.timezone == "America/Sao_Paulo"
        assert client.meta.ads.enabled is True
        assert client.meta.organic.enabled is True
        assert client.notifications.whatsapp.provider == "none"


def test_both_sources_disabled_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "invalid.yml"
        config = {
            **VALID_CONFIG,
            "meta": {
                **VALID_CONFIG["meta"],
                "ads": {"enabled": False},
                "organic": {"enabled": False},
            },
        }
        write_yaml(path, config)
        with pytest.raises(ConfigError):
            load_client_config(path)


def test_organic_without_instagram_id_raises():
    """organic.enabled=True but no instagram_business_id should fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "invalid.yml"
        config = {
            "slug": "test_client",
            "display_name": "Test",
            "meta": {
                "ad_account_id": "act_123",
                "access_token_env": "META_TOKEN_TEST",
                # instagram_business_id intentionally omitted
                "organic": {"enabled": True},
            },
        }
        write_yaml(path, config)
        with pytest.raises(ConfigError):
            load_client_config(path)


def test_organic_disabled_without_instagram_id_is_valid():
    """organic.enabled=False without instagram_business_id should be valid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "ads_only.yml"
        config = {
            "slug": "ads_only",
            "display_name": "Ads Only Client",
            "meta": {
                "ad_account_id": "act_123",
                "access_token_env": "META_TOKEN_TEST",
                "organic": {"enabled": False},
            },
        }
        write_yaml(path, config)
        client = load_client_config(path)
        assert client.meta.organic.enabled is False
        assert client.meta.instagram_business_id is None
