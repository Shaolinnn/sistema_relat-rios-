"""tests/test_ga4.py

Testes do normalizer e collector GA4 sem chamadas de rede.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from brandfield.normalizers.ga4 import GA4Normalizer
from brandfield.normalizers.models import GA4Metrics


# ── Fixtures ──────────────────────────────────────────────────

RAW_FIXTURE = {
    "property_id": "487849790",
    "period_start": "2025-03-01",
    "period_end": "2025-03-31",
    "daily": [
        {
            "date": "20250301",
            "sessions": 120,
            "users": 100,
            "new_users": 60,
            "pageviews": 300,
            "bounce_rate": 0.45,
            "avg_session_duration": 95.0,
            "conversions": 3,
        },
        {
            "date": "20250302",
            "sessions": 80,
            "users": 70,
            "new_users": 40,
            "pageviews": 200,
            "bounce_rate": 0.50,
            "avg_session_duration": 75.0,
            "conversions": 1,
        },
    ],
    "top_pages": [
        {"page_path": "/", "pageviews": 200, "avg_time_on_page": 60.0},
        {"page_path": "/contato", "pageviews": 150, "avg_time_on_page": 45.0},
    ],
    "top_sources": [
        {"source": "google", "medium": "organic", "sessions": 120},
        {"source": "instagram", "medium": "social", "sessions": 50},
    ],
}


# ── Normalizer ────────────────────────────────────────────────

class TestGA4Normalizer:

    def test_returns_none_for_empty_raw(self):
        result = GA4Normalizer().normalize({})
        assert result is None

    def test_basic_normalization(self):
        result = GA4Normalizer().normalize(RAW_FIXTURE)
        assert isinstance(result, GA4Metrics)

    def test_totals(self):
        result = GA4Normalizer().normalize(RAW_FIXTURE)
        assert result.total_sessions == 200        # 120 + 80
        assert result.total_users == 170           # 100 + 70
        assert result.total_new_users == 100       # 60 + 40
        assert result.total_pageviews == 500       # 300 + 200

    def test_weighted_bounce_rate(self):
        result = GA4Normalizer().normalize(RAW_FIXTURE)
        # (0.45*120 + 0.50*80) / 200 = (54 + 40) / 200 = 0.47
        assert result.avg_bounce_rate == pytest.approx(0.47, abs=1e-3)

    def test_weighted_avg_duration(self):
        result = GA4Normalizer().normalize(RAW_FIXTURE)
        # (95*120 + 75*80) / 200 = (11400 + 6000) / 200 = 87.0
        assert result.avg_session_duration == pytest.approx(87.0, abs=0.1)

    def test_daily_rows_sorted(self):
        result = GA4Normalizer().normalize(RAW_FIXTURE)
        dates = [r.date for r in result.daily]
        assert dates == sorted(dates)

    def test_period_dates(self):
        result = GA4Normalizer().normalize(RAW_FIXTURE)
        assert result.period_start == date(2025, 3, 1)
        assert result.period_end == date(2025, 3, 31)

    def test_top_pages_count(self):
        result = GA4Normalizer().normalize(RAW_FIXTURE)
        assert len(result.top_pages) == 2
        assert result.top_pages[0].page_path == "/"

    def test_top_sources_count(self):
        result = GA4Normalizer().normalize(RAW_FIXTURE)
        assert len(result.top_sources) == 2
        assert result.top_sources[0].source == "google"


# ── Collector (mock de rede) ──────────────────────────────────

class TestGA4CollectorDryRun:

    def _make_config(self, enabled: bool = True):
        """Cria um ClientConfig mínimo via MagicMock para teste."""
        return MagicMock(
            slug="test_client",
            google_analytics=MagicMock(
                property_id="487849790",
                credentials_env="GA4_TEST_KEY",
                enabled=enabled,
            ),
        )

    def test_collect_returns_empty_when_disabled(self):
        from brandfield.collectors.ga4 import GA4Collector

        config = self._make_config(enabled=False)
        collector = GA4Collector.__new__(GA4Collector)
        collector._slug = config.slug
        collector._ga4_cfg = config.google_analytics
        collector._property_id = config.google_analytics.property_id
        collector._credentials_env = config.google_analytics.credentials_env
        collector._start = "2025-03-01"
        collector._end = "2025-03-31"

        result = collector.collect()
        assert result == {}

    def test_missing_env_raises(self, monkeypatch):
        from brandfield.collectors.ga4 import GA4Collector

        monkeypatch.delenv("GA4_TEST_KEY", raising=False)

        config = self._make_config(enabled=True)
        collector = GA4Collector.__new__(GA4Collector)
        collector._slug = config.slug
        collector._ga4_cfg = config.google_analytics
        collector._property_id = "487849790"
        collector._credentials_env = "GA4_TEST_KEY"
        collector._start = "2025-03-01"
        collector._end = "2025-03-31"

        with pytest.raises(EnvironmentError, match="GA4_TEST_KEY"):
            collector._build_client()
