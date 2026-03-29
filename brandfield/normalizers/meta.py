"""Normalizes raw Meta Graph API responses into internal dataclasses."""

from datetime import date, datetime, timezone
from typing import Any

from brandfield.normalizers.models import CampaignMetrics, ClientSnapshot, OrganicMetrics


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def normalize_ads_response(
    client_slug: str,
    raw_ads: list[dict],
    report_date: date,
) -> list[CampaignMetrics]:
    """
    Convert a list of raw campaign insight dicts from Meta Graph API into
    CampaignMetrics dataclasses.

    Expected raw dict shape (one per campaign):
    {
        "campaign_id": "23843...",
        "campaign_name": "Black Friday Retargeting",
        "date_start": "2024-03-23",
        "date_stop": "2024-03-29",
        "impressions": "142500",
        "clicks": "3800",
        "spend": "4320.00",
        "cpm": "30.32",
        "cpc": "1.14",
        "purchase_roas": [{"action_type": "offsite_conversion.fb_pixel_purchase", "value": "3.2"}],
        "account_currency": "BRL",
    }
    """
    campaigns = []
    for raw in raw_ads:
        # ROAS comes as a list of action objects — extract the value
        roas = None
        roas_data = raw.get("purchase_roas")
        if roas_data and isinstance(roas_data, list) and roas_data:
            roas = _safe_float(roas_data[0].get("value"))
            if roas == 0.0:
                roas = None

        campaigns.append(
            CampaignMetrics(
                campaign_id=str(raw.get("campaign_id", "")),
                campaign_name=raw.get("campaign_name", "Unknown Campaign"),
                date_start=date.fromisoformat(raw.get("date_start", report_date.isoformat())),
                date_stop=date.fromisoformat(raw.get("date_stop", report_date.isoformat())),
                impressions=_safe_int(raw.get("impressions")),
                clicks=_safe_int(raw.get("clicks")),
                spend=_safe_float(raw.get("spend")),
                currency=raw.get("account_currency", "BRL"),
                cpm=_safe_float(raw.get("cpm")),
                cpc=_safe_float(raw.get("cpc")),
                roas=roas,
            )
        )
    return campaigns


def normalize_organic_response(
    raw_insights: list[dict],
    raw_follower_count: int,
    report_date: date,
) -> OrganicMetrics:
    """
    Convert raw Instagram organic insights (list of metric dicts) into
    an OrganicMetrics dataclass.

    Meta returns each metric as a separate entry:
    [
        {"name": "reach", "period": "day", "values": [{"value": 1200, "end_time": "..."}]},
        {"name": "impressions", "period": "day", "values": [...]},
        ...
    ]
    """
    metric_values: dict[str, int] = {}

    for metric_entry in raw_insights:
        name = metric_entry.get("name", "")
        values = metric_entry.get("values", [])
        if values:
            # Use the latest value (last entry in the list)
            metric_values[name] = _safe_int(values[-1].get("value", 0))

    return OrganicMetrics(
        date=report_date,
        reach=metric_values.get("reach", 0),
        impressions=metric_values.get("impressions", 0),
        profile_views=metric_values.get("profile_views", 0),
        follower_count=raw_follower_count,
        website_clicks=metric_values.get("website_clicks", 0),
    )


def build_snapshot(
    client_slug: str,
    report_date: date,
    campaigns: list[CampaignMetrics],
    organic: OrganicMetrics | None,
) -> ClientSnapshot:
    """Assemble a complete ClientSnapshot with a UTC timestamp."""
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ClientSnapshot(
        client_slug=client_slug,
        collected_at=collected_at,
        report_date=report_date,
        campaigns=campaigns,
        organic=organic,
    )
