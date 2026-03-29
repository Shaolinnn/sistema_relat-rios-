"""Tests for collectors in dry-run mode."""

from datetime import date

import pytest

from brandfield.collectors.meta_ads import MetaAdsCollector
from brandfield.collectors.instagram_organic import InstagramOrganicCollector
from brandfield.config.schema import MetaAdsConfig, MetaOrganicConfig


def test_meta_ads_dry_run_returns_fixture():
    collector = MetaAdsCollector(
        credentials={},
        ad_account_id="act_123",
        ads_config=MetaAdsConfig(),
        dry_run=True,
    )
    results = collector.collect(date(2024, 3, 23), date(2024, 3, 29))
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "campaign_name" in results[0]


def test_instagram_organic_dry_run_returns_fixture():
    collector = InstagramOrganicCollector(
        credentials={},
        instagram_business_id="17841400000000",
        organic_config=MetaOrganicConfig(),
        dry_run=True,
    )
    results = collector.collect(date(2024, 3, 23), date(2024, 3, 29))
    assert isinstance(results, list)
    # Should have at least one insight entry and follower_count
    names = [e.get("name") for e in results]
    assert "follower_count" in names


def test_meta_ads_raises_without_credentials():
    from brandfield.collectors.base import CollectorError
    collector = MetaAdsCollector(
        credentials={},
        ad_account_id="act_123",
        ads_config=MetaAdsConfig(),
        dry_run=False,  # real mode, no credentials
    )
    with pytest.raises(CollectorError, match="Missing access token"):
        collector.collect(date(2024, 3, 23), date(2024, 3, 29))
