"""Shared pytest fixtures."""

import json
from datetime import date
from pathlib import Path

import pytest

from brandfield.config.schema import (
    ClientConfig,
    MetaAdsConfig,
    MetaConfig,
    MetaOrganicConfig,
    NotificationsConfig,
    ReportConfig,
    WhatsAppConfig,
)
from brandfield.normalizers.models import CampaignMetrics, ClientSnapshot, OrganicMetrics

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_client_config() -> ClientConfig:
    return ClientConfig(
        slug="test_client",
        display_name="Test Client",
        timezone="America/Sao_Paulo",
        meta=MetaConfig(
            ad_account_id="act_123456789",
            instagram_business_id="17841400000000",
            access_token_env="META_TOKEN_TEST",
            ads=MetaAdsConfig(enabled=True, date_preset="last_7d"),
            organic=MetaOrganicConfig(enabled=True),
        ),
        notifications=NotificationsConfig(
            whatsapp=WhatsAppConfig(
                enabled=True,
                provider="none",
                recipient_phone="+5511999999999",
            )
        ),
        report=ReportConfig(),
    )


@pytest.fixture
def sample_campaign() -> CampaignMetrics:
    return CampaignMetrics(
        campaign_id="23843000000001",
        campaign_name="Black Friday Retargeting",
        date_start=date(2024, 3, 23),
        date_stop=date(2024, 3, 29),
        impressions=85000,
        clicks=2200,
        spend=2500.00,
        currency="BRL",
        cpm=29.41,
        cpc=1.14,
        roas=4.8,
    )


@pytest.fixture
def sample_organic() -> OrganicMetrics:
    return OrganicMetrics(
        date=date(2024, 3, 29),
        reach=5100,
        impressions=9800,
        profile_views=410,
        follower_count=12450,
        website_clicks=0,
    )


@pytest.fixture
def sample_snapshot(sample_campaign, sample_organic) -> ClientSnapshot:
    return ClientSnapshot(
        client_slug="test_client",
        collected_at="2024-03-29T08:00:00Z",
        report_date=date(2024, 3, 29),
        campaigns=[sample_campaign],
        organic=sample_organic,
    )


@pytest.fixture
def raw_ads_fixture() -> list[dict]:
    with (FIXTURES_DIR / "meta_ads_response.json").open() as f:
        return json.load(f)


@pytest.fixture
def raw_organic_fixture() -> list[dict]:
    with (FIXTURES_DIR / "instagram_organic_response.json").open() as f:
        return json.load(f)
