"""HTML report renderer using Jinja2 templates and Chart.js."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import jinja2

from brandfield.config.schema import ClientConfig
from brandfield.normalizers.models import ClientSnapshot
from brandfield.summary.executive import build_executive_summary

TEMPLATES_DIR = Path(__file__).parent / "templates"
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"


class HtmlRenderer:
    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )
        self.env.filters["json"] = json.dumps

    def render_client(
        self,
        client_config: ClientConfig,
        snapshots: list[ClientSnapshot],
        period: str = "daily",
    ) -> str:
        """Render a full HTML dashboard for one client."""
        template = self.env.get_template("client_report.html")

        # Prepare chart data series
        chart_labels = [s.report_date.strftime("%d/%m") for s in snapshots]
        spend_series = [round(s.total_spend, 2) for s in snapshots]
        impressions_series = [s.total_impressions for s in snapshots]
        clicks_series = [s.total_clicks for s in snapshots]
        follower_series = [
            s.organic.follower_count if s.organic else None for s in snapshots
        ]

        # Campaign breakdown for latest snapshot
        latest = snapshots[-1] if snapshots else None
        campaign_names = []
        campaign_spends = []
        if latest:
            for c in sorted(latest.campaigns, key=lambda x: x.spend, reverse=True):
                campaign_names.append(c.campaign_name)
                campaign_spends.append(round(c.spend, 2))

        # KPI values from aggregated data
        total_spend = sum(s.total_spend for s in snapshots)
        total_impressions = sum(s.total_impressions for s in snapshots)
        total_clicks = sum(s.total_clicks for s in snapshots)
        currency = snapshots[-1].currency if snapshots else "BRL"

        roas_values = [
            (c.roas, c.spend)
            for s in snapshots
            for c in s.campaigns
            if c.roas is not None and c.spend > 0
        ]
        avg_roas: Optional[float] = None
        if roas_values:
            avg_roas = sum(r * sp for r, sp in roas_values) / sum(sp for _, sp in roas_values)

        latest_organic = next(
            (s.organic for s in reversed(snapshots) if s.organic is not None), None
        )

        executive_summary = build_executive_summary(client_config, snapshots, period)
        generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M UTC")

        return template.render(
            client=client_config,
            snapshots=snapshots,
            latest=latest,
            period=period,
            generated_at=generated_at,
            # KPIs
            total_spend=total_spend,
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            avg_roas=avg_roas,
            currency=currency,
            latest_organic=latest_organic,
            # Chart.js data (passed as JSON strings)
            chart_labels=chart_labels,
            spend_series=spend_series,
            impressions_series=impressions_series,
            clicks_series=clicks_series,
            follower_series=follower_series,
            campaign_names=campaign_names,
            campaign_spends=campaign_spends,
            # Executive summary (for the HTML section too)
            executive_summary=executive_summary,
        )

    def render_index(self, all_clients: list[ClientConfig]) -> str:
        """Render the landing page listing all client dashboards."""
        template = self.env.get_template("index.html")
        generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M UTC")
        return template.render(clients=all_clients, generated_at=generated_at)

    def write_client_report(
        self,
        client_config: ClientConfig,
        snapshots: list[ClientSnapshot],
        period: str = "daily",
        docs_dir: Path = DOCS_DIR,
    ) -> Path:
        """Render and write the client report to docs/{slug}/index.html."""
        html = self.render_client(client_config, snapshots, period)
        output_dir = docs_dir / client_config.slug
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "index.html"
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def write_index(
        self,
        all_clients: list[ClientConfig],
        docs_dir: Path = DOCS_DIR,
    ) -> Path:
        """Render and write the index page to docs/index.html."""
        html = self.render_index(all_clients)
        docs_dir.mkdir(parents=True, exist_ok=True)
        output_path = docs_dir / "index.html"
        output_path.write_text(html, encoding="utf-8")
        return output_path
