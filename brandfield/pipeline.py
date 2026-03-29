"""Main pipeline orchestrator — runs the full collect → render → notify cycle."""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import jinja2

from brandfield.collectors.instagram_organic import InstagramOrganicCollector
from brandfield.collectors.meta_ads import MetaAdsCollector
from brandfield.collectors.base import CollectorError
from brandfield.config.loader import load_credentials
from brandfield.config.schema import ClientConfig
from brandfield.normalizers.meta import (
    build_snapshot,
    normalize_ads_response,
    normalize_organic_response,
)
from brandfield.normalizers.models import ClientSnapshot
from brandfield.notifications.base import NotificationError, NotificationMessage
from brandfield.notifications.factory import get_notifier
from brandfield.renderers.html_renderer import DOCS_DIR, HtmlRenderer
from brandfield.storage.json_store import DATA_DIR, JsonStore
from brandfield.summary.executive import build_executive_summary

logger = logging.getLogger(__name__)

# Maps date_preset values to the number of days to look back in history
_DATE_PRESET_DAYS: dict[str, int] = {
    "yesterday": 1,
    "last_7d": 7,
    "last_14d": 14,
    "last_30d": 30,
    "this_month": 30,   # approximate; history chart uses 30d regardless
    "last_month": 30,
}


def _today_in_timezone(tz_name: str) -> date:
    """Return today's date in the client's configured timezone."""
    from datetime import datetime, timezone as _tz
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        logger.warning("Unknown timezone %r, falling back to UTC", tz_name)
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date()


@dataclass
class RunResult:
    client_slug: str
    period: str
    success: bool
    errors: list[str] = field(default_factory=list)
    report_path: Optional[Path] = None
    notification_sent: bool = False

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        logger.error("[%s] %s", self.client_slug, msg)


class ReportPipeline:
    def __init__(
        self,
        client_config: ClientConfig,
        dry_run: bool = False,
        data_dir: Path = DATA_DIR,
        docs_dir: Path = DOCS_DIR,
    ):
        self.client = client_config
        self.dry_run = dry_run
        self.store = JsonStore(data_dir)
        self.renderer = HtmlRenderer()
        self.docs_dir = docs_dir

    def run(self, period: str = "daily") -> RunResult:
        """
        Execute the full pipeline for one client.

        Steps:
        1. Collect data from enabled sources
        2. Normalize to internal models
        3. Save snapshot to data/
        4. Load historical range for charts
        5. Render HTML report
        6. Build executive summary
        7. Send WhatsApp notification
        """
        result = RunResult(
            client_slug=self.client.slug,
            period=period,
            success=False,
        )

        # Use client's timezone so date boundaries are correct regardless of where
        # the server or GitHub Actions runner is located.
        today = _today_in_timezone(self.client.timezone)

        # ── Step 1 & 2: Collect + Normalize ──────────────────────────────
        credentials = load_credentials(self.client)

        # Determine collection window from the configured date_preset
        collection_days = _DATE_PRESET_DAYS.get(self.client.meta.ads.date_preset, 7)
        collection_start = today - timedelta(days=collection_days - 1)

        campaigns = []
        organic = None

        # Ads
        if self.client.meta.ads.enabled:
            try:
                ads_collector = MetaAdsCollector(
                    credentials=credentials,
                    ad_account_id=self.client.meta.ad_account_id,
                    ads_config=self.client.meta.ads,
                    dry_run=self.dry_run,
                )
                raw_ads = ads_collector.collect(
                    start_date=collection_start,
                    end_date=today,
                )
                campaigns = normalize_ads_response(
                    self.client.slug, raw_ads, report_date=today
                )
                logger.info(
                    "[%s] Collected %d campaigns", self.client.slug, len(campaigns)
                )
            except CollectorError as e:
                result.add_error(f"Ads collection failed: {e}")

        # Organic
        if self.client.meta.organic.enabled:
            try:
                organic_collector = InstagramOrganicCollector(
                    credentials=credentials,
                    instagram_business_id=self.client.meta.instagram_business_id,
                    organic_config=self.client.meta.organic,
                    dry_run=self.dry_run,
                )
                raw_organic = organic_collector.collect(
                    start_date=collection_start,
                    end_date=today,
                )
                follower_count = next(
                    (
                        entry["values"][-1]["value"]
                        for entry in raw_organic
                        if entry.get("name") == "follower_count"
                    ),
                    0,
                )
                insight_entries = [
                    e for e in raw_organic if e.get("name") != "follower_count"
                ]
                organic = normalize_organic_response(
                    insight_entries, follower_count, report_date=today
                )
                logger.info(
                    "[%s] Collected organic metrics (followers: %d)",
                    self.client.slug,
                    follower_count,
                )
            except CollectorError as e:
                result.add_error(f"Organic collection failed: {e}")

        # Abort if nothing was collected
        if not campaigns and organic is None:
            result.add_error("Nenhum dado coletado de nenhuma fonte. Abortando pipeline.")
            return result

        # ── Step 3: Build and save snapshot ──────────────────────────────
        snapshot = build_snapshot(
            client_slug=self.client.slug,
            report_date=today,
            campaigns=campaigns,
            organic=organic,
        )
        self.store.save(snapshot)
        logger.info("[%s] Snapshot saved for %s", self.client.slug, today.isoformat())

        # ── Step 4: Load historical range for charts ──────────────────────
        chart_days = collection_days if period == "daily" else max(collection_days, 30)
        history_start = today - timedelta(days=chart_days - 1)
        snapshots = self.store.load_range(
            self.client.slug, start=history_start, end=today
        )
        if not snapshots:
            snapshots = [snapshot]  # fallback to just today

        # ── Step 5: Render HTML report ────────────────────────────────────
        try:
            report_path = self.renderer.write_client_report(
                self.client, snapshots, period=period, docs_dir=self.docs_dir
            )
            result.report_path = report_path
            logger.info("[%s] Report written to %s", self.client.slug, report_path)
        except (jinja2.TemplateError, OSError) as e:
            result.add_error(f"HTML rendering failed: {e}")
            return result

        # ── Step 6 & 7: Summary + WhatsApp notification ───────────────────
        wa_config = self.client.notifications.whatsapp
        if wa_config.enabled:
            try:
                provider = "none" if self.dry_run else wa_config.provider
                # Pass credentials so providers can fall back to env vars.
                # WhatsApp providers use their own env var names (META_WA_TOKEN etc.)
                # rather than the per-client Meta token, so credentials dict is empty here.
                notifier = get_notifier(provider, credentials={})
                summary_text = build_executive_summary(self.client, snapshots, period)
                msg = NotificationMessage(
                    recipient_phone=wa_config.recipient_phone,
                    text=summary_text,
                )
                notifier.send_message(msg)
                result.notification_sent = True
                logger.info(
                    "[%s] WhatsApp notification sent via %s",
                    self.client.slug,
                    notifier.provider_name,
                )
            except NotificationError as e:
                # Non-fatal: report is published, only notify fails
                result.add_error(f"WhatsApp notification failed: {e}")

        result.success = True
        return result
