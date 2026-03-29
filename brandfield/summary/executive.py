"""Builds plain-text executive summaries formatted for WhatsApp."""

from datetime import date, timedelta
from typing import Optional

from brandfield.config.schema import ClientConfig
from brandfield.normalizers.models import ClientSnapshot, GA4Metrics


def _fmt_currency(value: float, currency: str) -> str:
    """Format a monetary value with currency symbol."""
    symbol = "R$" if currency == "BRL" else "$"
    return f"{symbol} {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_number(value: int) -> str:
    """Format a large integer with dot thousands separator (Brazilian style)."""
    return f"{value:,}".replace(",", ".")


def _fmt_roas(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}x"


def _fmt_duration(seconds: float) -> str:
    """Converte segundos para 'Xmin Ys'."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m > 0:
        return f"{m}min {s}s"
    return f"{s}s"


def _ga4_section(ga4: GA4Metrics) -> str:
    """Retorna o bloco de texto '🌐 Site' para o resumo WhatsApp."""
    bounce_pct = round(ga4.avg_bounce_rate * 100, 1)
    duration_fmt = _fmt_duration(ga4.avg_session_duration)
    new_pct = (
        round(ga4.total_new_users / ga4.total_users * 100, 1)
        if ga4.total_users > 0
        else 0.0
    )

    top_pages_lines = "\n".join(
        f"  {i + 1}. {p.page_path} ({p.pageviews:,} views)".replace(",", ".")
        for i, p in enumerate(ga4.top_pages[:3])
    )

    top_sources_lines = "\n".join(
        f"  {i + 1}. {s.source} / {s.medium} ({s.sessions:,} sessões)".replace(",", ".")
        for i, s in enumerate(ga4.top_sources[:3])
    )

    lines = [
        "*🌐 Site (GA4)*",
        f"Sessões: {_fmt_number(ga4.total_sessions)}",
        f"Usuários: {_fmt_number(ga4.total_users)} ({new_pct}% novos)",
        f"Pageviews: {_fmt_number(ga4.total_pageviews)}",
        f"Bounce rate: {bounce_pct}%",
        f"Duração média: {duration_fmt}",
    ]
    if top_pages_lines:
        lines += ["", f"📄 Top páginas:\n{top_pages_lines}"]
    if top_sources_lines:
        lines += ["", f"📡 Top fontes:\n{top_sources_lines}"]
    return "\n".join(lines)


def _top_campaign(snapshots: list[ClientSnapshot]) -> Optional[str]:
    """Find the campaign with highest ROAS across the given snapshots."""
    best = None
    best_roas = 0.0

    for snapshot in snapshots:
        for campaign in snapshot.campaigns:
            if campaign.roas and campaign.roas > best_roas:
                best_roas = campaign.roas
                best = campaign

    if best is None:
        return None

    return (
        f'"{best.campaign_name}"\n'
        f"  → {_fmt_currency(best.spend, best.currency)} spend | {_fmt_roas(best.roas)} ROAS"
    )


def build_executive_summary(
    client_config: ClientConfig,
    snapshots: list[ClientSnapshot],
    period: str,  # "daily" or "weekly"
) -> str:
    """
    Build a plain-text executive summary formatted for WhatsApp.

    WhatsApp renders *text* as bold. Uses emoji for visual hierarchy.
    Returns an empty string if no snapshots are provided.
    """
    if not snapshots:
        return (
            f"📊 *{client_config.display_name}*\n"
            f"Nenhum dado disponível para este período."
        )

    # ── Period label ──────────────────────────────────────────────────────
    if period == "daily":
        report_date = snapshots[-1].report_date
        period_label = report_date.strftime("%d/%m/%Y")
    else:
        start = snapshots[0].report_date
        end = snapshots[-1].report_date
        period_label = f"{start.strftime('%d/%m')}–{end.strftime('%d/%m/%Y')}"

    period_name = "Relatório Diário" if period == "daily" else "Relatório Semanal"

    # ── Aggregate ads metrics across all snapshots ────────────────────────
    total_spend = sum(s.total_spend for s in snapshots)
    total_impressions = sum(s.total_impressions for s in snapshots)
    total_clicks = sum(s.total_clicks for s in snapshots)
    currency = snapshots[-1].currency

    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0

    # Average ROAS weighted by spend
    roas_values = [
        (c.roas, c.spend)
        for s in snapshots
        for c in s.campaigns
        if c.roas is not None and c.spend > 0
    ]
    avg_roas: Optional[float] = None
    if roas_values:
        weighted_sum = sum(r * sp for r, sp in roas_values)
        total_weight = sum(sp for _, sp in roas_values)
        avg_roas = weighted_sum / total_weight if total_weight > 0 else None

    # ── Organic metrics (latest snapshot that has organic data) ──────────
    organic_snapshot = next(
        (s for s in reversed(snapshots) if s.organic is not None), None
    )

    # ── Assemble message ──────────────────────────────────────────────────
    lines = [
        f"📊 *{client_config.display_name} — {period_name} ({period_label})*",
        "",
    ]

    # Ads section
    if any(s.campaigns for s in snapshots):
        lines += [
            "*📣 Meta Ads*",
            f"💰 Investimento: {_fmt_currency(total_spend, currency)}",
            f"📈 ROAS: {_fmt_roas(avg_roas)}",
            f"👁️ Impressões: {_fmt_number(total_impressions)}",
            f"🖱️ Cliques: {_fmt_number(total_clicks)} (CTR: {ctr:.2f}%)",
        ]

        top = _top_campaign(snapshots)
        if top:
            lines += ["", f"🏆 Top Campanha: {top}"]

        lines.append("")

    # Organic section
    if organic_snapshot and organic_snapshot.organic:
        org = organic_snapshot.organic
        lines += [
            "*📱 Instagram Orgânico*",
            f"Alcance: {_fmt_number(org.reach)}",
            f"Impressões: {_fmt_number(org.impressions)}",
            f"Seguidores: {_fmt_number(org.follower_count)}",
        ]
        if org.profile_views:
            lines.append(f"Visitas ao perfil: {_fmt_number(org.profile_views)}")
        lines.append("")

    # GA4 section (latest snapshot that has ga4 data)
    ga4_snapshot = next((s for s in reversed(snapshots) if s.ga4 is not None), None)
    if ga4_snapshot and ga4_snapshot.ga4:
        lines += [_ga4_section(ga4_snapshot.ga4), ""]

    lines.append("_Gerado automaticamente pelo BrandField Reports_")

    return "\n".join(lines)
