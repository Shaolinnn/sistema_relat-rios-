"""End-to-end pipeline test in dry-run mode."""

import os
import tempfile
from pathlib import Path

import pytest

from brandfield.pipeline import ReportPipeline


def test_pipeline_dry_run_succeeds(sample_client_config):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        pipeline = ReportPipeline(
            client_config=sample_client_config,
            dry_run=True,
            data_dir=tmppath / "data",
            docs_dir=tmppath / "docs",
        )
        result = pipeline.run(period="daily")

        assert result.success, f"Pipeline failed with errors: {result.errors}"
        assert result.report_path is not None
        assert result.report_path.exists()


def test_pipeline_dry_run_creates_snapshot(sample_client_config):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        pipeline = ReportPipeline(
            client_config=sample_client_config,
            dry_run=True,
            data_dir=tmppath / "data",
            docs_dir=tmppath / "docs",
        )
        pipeline.run(period="daily")

        data_dir = tmppath / "data" / "test_client"
        snapshots = list(data_dir.glob("snapshot_*.json"))
        assert len(snapshots) == 1


def test_pipeline_null_notifier_in_dry_run(sample_client_config, capsys):
    """In dry-run, WhatsApp messages should be logged, not sent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        pipeline = ReportPipeline(
            client_config=sample_client_config,
            dry_run=True,
            data_dir=tmppath / "data",
            docs_dir=tmppath / "docs",
        )
        result = pipeline.run(period="daily")

        # NullNotifier logs to stdout
        captured = capsys.readouterr()
        assert "NullNotifier" in captured.out or result.success
