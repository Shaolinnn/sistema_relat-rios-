"""Converte o dict raw retornado por GA4Collector em GA4Metrics."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict

from brandfield.normalizers.models import (
    GA4DailyRow,
    GA4Metrics,
    GA4TopPage,
    GA4TopSource,
)


def _parse_date(s: str) -> date:
    """Aceita YYYYMMDD (GA4) ou YYYY-MM-DD."""
    s = s.strip()
    if len(s) == 8:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return date.fromisoformat(s)


class GA4Normalizer:
    """Transforma raw GA4 dict → GA4Metrics dataclass."""

    def normalize(self, raw: Dict[str, Any]) -> GA4Metrics | None:
        if not raw:
            return None

        daily_rows = [
            GA4DailyRow(
                date=_parse_date(r["date"]),
                sessions=r["sessions"],
                users=r["users"],
                new_users=r["new_users"],
                pageviews=r["pageviews"],
                bounce_rate=r["bounce_rate"],
                avg_session_duration=r["avg_session_duration"],
                conversions=r["conversions"],
            )
            for r in raw.get("daily", [])
        ]

        top_pages = [
            GA4TopPage(
                page_path=p["page_path"],
                pageviews=p["pageviews"],
                avg_time_on_page=p["avg_time_on_page"],
            )
            for p in raw.get("top_pages", [])
        ]

        top_sources = [
            GA4TopSource(
                source=s["source"],
                medium=s["medium"],
                sessions=s["sessions"],
            )
            for s in raw.get("top_sources", [])
        ]

        # ── Totais agregados ───────────────────────────────────────────────
        total_sessions = sum(r.sessions for r in daily_rows)
        total_users = sum(r.users for r in daily_rows)
        total_new_users = sum(r.new_users for r in daily_rows)
        total_pageviews = sum(r.pageviews for r in daily_rows)

        # Bounce rate: média ponderada por sessões
        if total_sessions > 0:
            avg_bounce = (
                sum(r.bounce_rate * r.sessions for r in daily_rows) / total_sessions
            )
        else:
            avg_bounce = 0.0

        # Duração média ponderada por sessões
        if total_sessions > 0:
            avg_duration = (
                sum(r.avg_session_duration * r.sessions for r in daily_rows)
                / total_sessions
            )
        else:
            avg_duration = 0.0

        return GA4Metrics(
            property_id=raw["property_id"],
            period_start=_parse_date(raw["period_start"]),
            period_end=_parse_date(raw["period_end"]),
            total_sessions=total_sessions,
            total_users=total_users,
            total_new_users=total_new_users,
            total_pageviews=total_pageviews,
            avg_bounce_rate=round(avg_bounce, 4),
            avg_session_duration=round(avg_duration, 1),
            daily=daily_rows,
            top_pages=top_pages,
            top_sources=top_sources,
        )
