"""Collects Meta Ads campaign insights via the facebook-business SDK."""

from datetime import date

from brandfield.collectors.base import BaseCollector, CollectorError
from brandfield.config.schema import MetaAdsConfig


class MetaAdsCollector(BaseCollector):
    """
    Fetches campaign-level Ad insights from the Meta Graph API.

    Returns a list of raw campaign dicts ready for normalization.
    Each dict matches the shape in tests/fixtures/meta_ads_response.json.
    """

    FIXTURE_FILE = "meta_ads_response.json"

    def __init__(
        self,
        credentials: dict,
        ad_account_id: str,
        ads_config: MetaAdsConfig,
        dry_run: bool = False,
    ):
        super().__init__(credentials, dry_run)
        self.ad_account_id = ad_account_id
        self.ads_config = ads_config

    def collect(self, start_date: date, end_date: date) -> list[dict]:
        if self.dry_run:
            return self.load_fixture(self.FIXTURE_FILE)

        return self._fetch_from_api(start_date, end_date)

    def _fetch_from_api(self, start_date: date, end_date: date) -> list[dict]:
        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.adobjects.adaccount import AdAccount
        except ImportError as e:
            raise CollectorError(
                "facebook-business package not installed. "
                "Run: pip install facebook-business"
            ) from e

        access_token = self.credentials.get("access_token")
        if not access_token:
            raise CollectorError(
                f"Missing access token for account {self.ad_account_id}. "
                "Check your environment variables."
            )

        try:
            FacebookAdsApi.init(access_token=access_token)
            account = AdAccount(self.ad_account_id)

            params = {
                "level": "campaign",
                "date_preset": self.ads_config.date_preset,
                "fields": self.ads_config.metrics + [
                    "campaign_id",
                    "campaign_name",
                    "date_start",
                    "date_stop",
                    "account_currency",
                ],
            }

            # Filter by specific campaign IDs if configured
            if self.ads_config.campaign_ids:
                params["filtering"] = [
                    {
                        "field": "campaign.id",
                        "operator": "IN",
                        "value": self.ads_config.campaign_ids,
                    }
                ]

            insights_cursor = account.get_insights(params=params)
            results = []
            for insight in insights_cursor:
                results.append(dict(insight))

            return results

        except Exception as e:
            # Wrap all SDK exceptions so callers only deal with CollectorError
            raise CollectorError(
                f"Meta Ads API error for account {self.ad_account_id}: {e}"
            ) from e
