"""Collects Instagram organic metrics via the Meta Graph API."""

from datetime import date

import requests

from brandfield.collectors.base import BaseCollector, CollectorError
from brandfield.config.schema import MetaOrganicConfig


GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

# Metrics supported by the Instagram Business insights endpoint
SUPPORTED_INSIGHT_METRICS = {
    "reach",
    "impressions",
    "profile_views",
    "website_clicks",
}


class InstagramOrganicCollector(BaseCollector):
    """
    Fetches Instagram organic insights and follower count via the Meta Graph API.

    Returns a tuple of (insights_list, follower_count).
    insights_list matches the shape in tests/fixtures/instagram_organic_response.json.
    """

    FIXTURE_FILE = "instagram_organic_response.json"

    def __init__(
        self,
        credentials: dict,
        instagram_business_id: str,
        organic_config: MetaOrganicConfig,
        dry_run: bool = False,
    ):
        super().__init__(credentials, dry_run)
        self.instagram_business_id = instagram_business_id
        self.organic_config = organic_config

    def collect(self, start_date: date, end_date: date) -> list[dict]:
        """
        Returns a list with two items:
        [0] — list of insight metric dicts (from /insights endpoint)
        [1] — dict with {"follower_count": int}
        """
        if self.dry_run:
            return self.load_fixture(self.FIXTURE_FILE)

        return self._fetch_from_api(start_date, end_date)

    def _fetch_from_api(self, start_date: date, end_date: date) -> list[dict]:
        access_token = self.credentials.get("access_token")
        if not access_token:
            raise CollectorError(
                f"Missing access token for Instagram account {self.instagram_business_id}."
            )

        try:
            # Filter to only supported insight metrics (exclude follower_count which
            # is fetched separately as a profile field)
            insight_metrics = [
                m for m in self.organic_config.metrics
                if m in SUPPORTED_INSIGHT_METRICS
            ]

            results = []

            # Fetch time-series insights for supported metrics
            if insight_metrics:
                insights_url = f"{GRAPH_API_BASE}/{self.instagram_business_id}/insights"
                resp = requests.get(
                    insights_url,
                    params={
                        "metric": ",".join(insight_metrics),
                        "period": "day",
                        "since": start_date.isoformat(),
                        "until": end_date.isoformat(),
                        "access_token": access_token,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                results.extend(resp.json().get("data", []))

            # Fetch point-in-time follower count from the profile endpoint
            profile_url = f"{GRAPH_API_BASE}/{self.instagram_business_id}"
            resp = requests.get(
                profile_url,
                params={
                    "fields": "followers_count",
                    "access_token": access_token,
                },
                timeout=30,
            )
            resp.raise_for_status()
            profile_data = resp.json()
            results.append({
                "name": "follower_count",
                "values": [{"value": profile_data.get("followers_count", 0)}],
            })

            return results

        except requests.HTTPError as e:
            raise CollectorError(
                f"Instagram API HTTP error for account {self.instagram_business_id}: {e}"
            ) from e
        except requests.RequestException as e:
            raise CollectorError(
                f"Instagram API request failed for account {self.instagram_business_id}: {e}"
            ) from e
