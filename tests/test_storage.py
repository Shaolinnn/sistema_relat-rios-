"""Tests for JsonStore."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from brandfield.storage.json_store import JsonStore


def test_save_and_load(sample_snapshot):
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JsonStore(base_path=Path(tmpdir))
        store.save(sample_snapshot)

        loaded = store.load("test_client", date(2024, 3, 29))
        assert loaded is not None
        assert loaded.client_slug == "test_client"
        assert loaded.report_date == date(2024, 3, 29)
        assert len(loaded.campaigns) == 1
        assert loaded.campaigns[0].campaign_name == "Black Friday Retargeting"


def test_load_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JsonStore(base_path=Path(tmpdir))
        result = store.load("nonexistent", date(2024, 1, 1))
        assert result is None


def test_load_range(sample_snapshot):
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JsonStore(base_path=Path(tmpdir))

        # Save 3 snapshots on different dates
        from dataclasses import replace
        for day in [27, 28, 29]:
            s = replace(sample_snapshot, report_date=date(2024, 3, day))
            # Manually update campaign dates too
            store.save(s)

        results = store.load_range("test_client", date(2024, 3, 27), date(2024, 3, 29))
        assert len(results) == 3
        assert results[0].report_date == date(2024, 3, 27)
        assert results[-1].report_date == date(2024, 3, 29)


def test_save_is_idempotent(sample_snapshot):
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JsonStore(base_path=Path(tmpdir))
        store.save(sample_snapshot)
        store.save(sample_snapshot)  # second save should not fail

        loaded = store.load("test_client", date(2024, 3, 29))
        assert loaded is not None


def test_roundtrip_serialization(sample_snapshot):
    """Ensure to_dict() → from_dict() preserves all fields."""
    data = sample_snapshot.to_dict()
    restored = type(sample_snapshot).from_dict(data)

    assert restored.client_slug == sample_snapshot.client_slug
    assert restored.report_date == sample_snapshot.report_date
    assert restored.campaigns[0].roas == sample_snapshot.campaigns[0].roas
    assert restored.organic.follower_count == sample_snapshot.organic.follower_count
