"""Coleta dados da Google Analytics Data API v1 (GA4).

Dependências:
    google-analytics-data>=0.18.0

Variável de ambiente esperada (nome configurável via YAML):
    GA4_SERVICE_ACCOUNT_JSON  →  conteúdo completo do JSON da service account.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from typing import Any, Dict

from brandfield.config.schema import ClientConfig

logger = logging.getLogger(__name__)


def _period_dates(period: str) -> tuple[str, str]:
    """Retorna (start_date, end_date) no formato YYYY-MM-DD."""
    today = date.today()

    if period == "daily":
        d = today - timedelta(days=1)
        return str(d), str(d)

    if period == "weekly":
        end = today - timedelta(days=today.weekday() + 1)  # último domingo
        start = end - timedelta(days=6)
        return str(start), str(end)

    if period == "monthly":
        first_of_this = today.replace(day=1)
        last_of_prev = first_of_this - timedelta(days=1)
        first_of_prev = last_of_prev.replace(day=1)
        return str(first_of_prev), str(last_of_prev)

    # fallback: últimos 30 dias
    return str(today - timedelta(days=30)), str(today - timedelta(days=1))


class GA4CollectorError(Exception):
    """Raised when GA4 data collection fails."""


class GA4Collector:
    """
    Coleta sessões, usuários, pageviews, bounce rate, top páginas
    e top fontes de tráfego de uma propriedade GA4.
    """

    def __init__(self, config: ClientConfig, period: str = "daily") -> None:
        self._ga4_cfg = config.google_analytics
        if self._ga4_cfg is None:
            raise ValueError(
                f"Cliente '{config.slug}' não tem google_analytics configurado no YAML."
            )
        self._slug = config.slug
        self._property_id = self._ga4_cfg.property_id
        self._credentials_env = self._ga4_cfg.credentials_env
        self._start, self._end = _period_dates(period)

    # ── Autenticação ──────────────────────────────────────────────────────

    def _build_client(self) -> Any:
        """Cria o BetaAnalyticsDataClient autenticado via service account."""
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account

        raw_json = os.environ.get(self._credentials_env)
        if not raw_json:
            raise EnvironmentError(
                f"Variável de ambiente '{self._credentials_env}' não encontrada. "
                "Defina-a com o conteúdo JSON da service account."
            )

        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"'{self._credentials_env}' não contém JSON válido."
            ) from exc

        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        return BetaAnalyticsDataClient(credentials=credentials)

    # ── Requests ──────────────────────────────────────────────────────────

    def _run_report(self, client: Any, dimensions: list, metrics: list) -> Any:
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )

        request = RunReportRequest(
            property=f"properties/{self._property_id}",
            date_ranges=[DateRange(start_date=self._start, end_date=self._end)],
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
        )
        return client.run_report(request)

    def _collect_daily_series(self, client: Any) -> list[dict]:
        response = self._run_report(
            client,
            dimensions=["date"],
            metrics=[
                "sessions",
                "totalUsers",
                "newUsers",
                "screenPageViews",
                "bounceRate",
                "averageSessionDuration",
                "conversions",
            ],
        )
        rows = []
        for row in response.rows:
            rows.append(
                {
                    "date": row.dimension_values[0].value,  # YYYYMMDD
                    "sessions": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                    "new_users": int(row.metric_values[2].value),
                    "pageviews": int(row.metric_values[3].value),
                    "bounce_rate": float(row.metric_values[4].value),
                    "avg_session_duration": float(row.metric_values[5].value),
                    "conversions": int(row.metric_values[6].value),
                }
            )
        return sorted(rows, key=lambda r: r["date"])

    def _collect_top_pages(self, client: Any, limit: int = 10) -> list[dict]:
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            OrderBy,
            RunReportRequest,
        )

        request = RunReportRequest(
            property=f"properties/{self._property_id}",
            date_ranges=[DateRange(start_date=self._start, end_date=self._end)],
            dimensions=[Dimension(name="pagePath")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
            ],
            order_bys=[
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
                    desc=True,
                )
            ],
            limit=limit,
        )
        response = client.run_report(request)

        return [
            {
                "page_path": row.dimension_values[0].value,
                "pageviews": int(row.metric_values[0].value),
                "avg_time_on_page": float(row.metric_values[1].value),
            }
            for row in response.rows
        ]

    def _collect_top_sources(self, client: Any, limit: int = 10) -> list[dict]:
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            OrderBy,
            RunReportRequest,
        )

        request = RunReportRequest(
            property=f"properties/{self._property_id}",
            date_ranges=[DateRange(start_date=self._start, end_date=self._end)],
            dimensions=[
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
            ],
            metrics=[Metric(name="sessions")],
            order_bys=[
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                    desc=True,
                )
            ],
            limit=limit,
        )
        response = client.run_report(request)

        return [
            {
                "source": row.dimension_values[0].value,
                "medium": row.dimension_values[1].value,
                "sessions": int(row.metric_values[0].value),
            }
            for row in response.rows
        ]

    # ── Interface pública ─────────────────────────────────────────────────

    def collect(self) -> Dict[str, Any]:
        """
        Retorna dict raw com todas as seções.
        O GA4Normalizer converte para GA4Metrics.
        """
        if not self._ga4_cfg.enabled:
            logger.info("GA4 desabilitado para '%s' — pulando coleta.", self._slug)
            return {}

        logger.info(
            "Coletando GA4 property=%s período=%s→%s",
            self._property_id,
            self._start,
            self._end,
        )

        try:
            client = self._build_client()
            daily = self._collect_daily_series(client)
            top_pages = self._collect_top_pages(client)
            top_sources = self._collect_top_sources(client)
        except (EnvironmentError, ValueError):
            raise
        except Exception as exc:
            raise GA4CollectorError(f"Falha ao coletar dados GA4: {exc}") from exc

        return {
            "property_id": self._property_id,
            "period_start": self._start,
            "period_end": self._end,
            "daily": daily,
            "top_pages": top_pages,
            "top_sources": top_sources,
        }
