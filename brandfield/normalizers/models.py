"""Internal data models — typed dataclasses that represent normalized report data."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class CampaignMetrics:
    campaign_id: str
    campaign_name: str
    date_start: date
    date_stop: date
    impressions: int
    clicks: int
    spend: float        # always in account currency
    currency: str
    cpm: float
    cpc: float
    roas: Optional[float] = None  # None when no conversion tracking configured


@dataclass
class OrganicMetrics:
    date: date
    reach: int
    impressions: int
    profile_views: int
    follower_count: int
    website_clicks: int = 0


@dataclass
class ClientSnapshot:
    """Complete daily snapshot for one client. This is the unit stored to disk."""
    client_slug: str
    collected_at: str           # ISO 8601 UTC, e.g. "2024-03-29T08:00:00Z"
    report_date: date
    campaigns: list[CampaignMetrics] = field(default_factory=list)
    organic: Optional[OrganicMetrics] = None

    # ── Aggregate helpers ──────────────────────────────────────────────────

    @property
    def total_spend(self) -> float:
        return sum(c.spend for c in self.campaigns)

    @property
    def total_impressions(self) -> int:
        return sum(c.impressions for c in self.campaigns)

    @property
    def total_clicks(self) -> int:
        return sum(c.clicks for c in self.campaigns)

    @property
    def avg_roas(self) -> Optional[float]:
        roas_values = [c.roas for c in self.campaigns if c.roas is not None]
        if not roas_values:
            return None
        return sum(roas_values) / len(roas_values)

    @property
    def currency(self) -> str:
        if self.campaigns:
            return self.campaigns[0].currency
        return "BRL"

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "client_slug": self.client_slug,
            "collected_at": self.collected_at,
            "report_date": self.report_date.isoformat(),
            "campaigns": [
                {
                    "campaign_id": c.campaign_id,
                    "campaign_name": c.campaign_name,
                    "date_start": c.date_start.isoformat(),
                    "date_stop": c.date_stop.isoformat(),
                    "impressions": c.impressions,
                    "clicks": c.clicks,
                    "spend": c.spend,
                    "currency": c.currency,
                    "cpm": c.cpm,
                    "cpc": c.cpc,
                    "roas": c.roas,
                }
                for c in self.campaigns
            ],
            "organic": (
                {
                    "date": self.organic.date.isoformat(),
                    "reach": self.organic.reach,
                    "impressions": self.organic.impressions,
                    "profile_views": self.organic.profile_views,
                    "follower_count": self.organic.follower_count,
                    "website_clicks": self.organic.website_clicks,
                }
                if self.organic
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClientSnapshot":
        """Deserialize from a stored JSON dict."""
        campaigns = [
            CampaignMetrics(
                campaign_id=c["campaign_id"],
                campaign_name=c["campaign_name"],
                date_start=date.fromisoformat(c["date_start"]),
                date_stop=date.fromisoformat(c["date_stop"]),
                impressions=c["impressions"],
                clicks=c["clicks"],
                spend=c["spend"],
                currency=c["currency"],
                cpm=c["cpm"],
                cpc=c["cpc"],
                roas=c.get("roas"),
            )
            for c in data.get("campaigns", [])
        ]

        organic = None
        if data.get("organic"):
            o = data["organic"]
            organic = OrganicMetrics(
                date=date.fromisoformat(o["date"]),
                reach=o["reach"],
                impressions=o["impressions"],
                profile_views=o["profile_views"],
                follower_count=o["follower_count"],
                website_clicks=o.get("website_clicks", 0),
            )

        return cls(
            client_slug=data["client_slug"],
            collected_at=data["collected_at"],
            report_date=date.fromisoformat(data["report_date"]),
            campaigns=campaigns,
            organic=organic,
        )
