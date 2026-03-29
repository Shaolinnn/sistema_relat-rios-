"""Tests for the HTML renderer."""

import tempfile
from pathlib import Path

import pytest

from brandfield.renderers.html_renderer import HtmlRenderer


def test_render_client_contains_client_name(sample_client_config, sample_snapshot):
    renderer = HtmlRenderer()
    html = renderer.render_client(sample_client_config, [sample_snapshot])
    assert "Test Client" in html
    assert "Chart.js" in html or "chart.js" in html.lower()


def test_render_client_contains_kpi_values(sample_client_config, sample_snapshot):
    renderer = HtmlRenderer()
    html = renderer.render_client(sample_client_config, [sample_snapshot])
    # Should contain spend value
    assert "2.500" in html or "2500" in html


def test_render_client_contains_campaign_name(sample_client_config, sample_snapshot):
    renderer = HtmlRenderer()
    html = renderer.render_client(sample_client_config, [sample_snapshot])
    assert "Black Friday Retargeting" in html


def test_render_index_contains_client_link(sample_client_config):
    renderer = HtmlRenderer()
    html = renderer.render_index([sample_client_config])
    assert "Test Client" in html
    assert "test_client/" in html


def test_write_client_report_creates_file(sample_client_config, sample_snapshot):
    renderer = HtmlRenderer()
    with tempfile.TemporaryDirectory() as tmpdir:
        docs_dir = Path(tmpdir)
        path = renderer.write_client_report(
            sample_client_config, [sample_snapshot], docs_dir=docs_dir
        )
        assert path.exists()
        assert path.name == "index.html"
        content = path.read_text()
        assert "Test Client" in content


def test_render_empty_snapshots(sample_client_config):
    """Renderer should not crash with empty snapshot list."""
    renderer = HtmlRenderer()
    html = renderer.render_client(sample_client_config, [])
    assert "Test Client" in html
