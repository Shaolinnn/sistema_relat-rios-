"""Tests for the Meta normalization layer."""

from datetime import date

from brandfield.normalizers.meta import (
    build_snapshot,
    normalize_ads_response,
    normalize_organic_response,
)
from brandfield.normalizers.models import CampaignMetrics, OrganicMetrics


def test_normalize_ads_response(raw_ads_fixture):
    campaigns = normalize_ads_response("test_client", raw_ads_fixture, date(2024, 3, 29))
    assert len(campaigns) == 2
    first = campaigns[0]
    assert isinstance(first, CampaignMetrics)
    assert first.campaign_name == "Black Friday Retargeting"
    assert first.impressions == 85000
    assert first.spend == 2500.0
    assert first.roas == 4.8
    assert first.currency == "BRL"


def test_normalize_ads_missing_roas():
    raw = [
        {
            "campaign_id": "1",
            "campaign_name": "Test",
            "date_start": "2024-03-23",
            "date_stop": "2024-03-29",
            "impressions": "1000",
            "clicks": "50",
            "spend": "100.00",
            "cpm": "100.0",
            "cpc": "2.0",
            "account_currency": "BRL",
        }
    ]
    campaigns = normalize_ads_response("slug", raw, date(2024, 3, 29))
    assert campaigns[0].roas is None


def test_normalize_organic_response(raw_organic_fixture):
    insight_entries = [e for e in raw_organic_fixture if e.get("name") != "follower_count"]
    organic = normalize_organic_response(insight_entries, 12450, date(2024, 3, 29))
    assert isinstance(organic, OrganicMetrics)
    assert organic.reach == 5100
    assert organic.impressions == 9800
    assert organic.profile_views == 410
    assert organic.follower_count == 12450


def test_build_snapshot(raw_ads_fixture, raw_organic_fixture):
    today = date(2024, 3, 29)
    campaigns = normalize_ads_response("test_client", raw_ads_fixture, today)
    insight_entries = [e for e in raw_organic_fixture if e.get("name") != "follower_count"]
    organic = normalize_organic_response(insight_entries, 12450, today)
    snapshot = build_snapshot("test_client", today, campaigns, organic)
    assert snapshot.client_slug == "test_client"
    assert snapshot.report_date == today
    assert len(snapshot.campaigns) == 2
    assert snapshot.organic is not None
    assert snapshot.total_spend == 2500.0 + 1820.0
