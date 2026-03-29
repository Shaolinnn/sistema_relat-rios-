# BrandField Reporting System

Automated reporting for marketing agencies. Collects data from Meta Graph API (Ads + Instagram Organic), generates HTML dashboards published to GitHub Pages, and sends executive summaries via WhatsApp.

## Architecture

```
Collect → Normalize → Store → Render → Publish → Notify
```

- **Config-driven**: Add a new client by creating one YAML file — no code changes needed
- **Dry-run mode**: Full pipeline runs locally without any API credentials
- **Pluggable WhatsApp**: Swap providers (Meta, Twilio, Evolution) with one config line

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env

# Validate client configs
python -m brandfield validate-config

# Run full pipeline in dry-run mode (no API calls, no WhatsApp)
python -m brandfield run --period daily --dry-run

# Open the generated report
open docs/example_client/index.html
```

## Adding a New Client

1. Copy `clients/_template.yml` to `clients/{client_slug}.yml`
2. Fill in the Meta account IDs and choose a WhatsApp provider
3. Add the client's Meta access token as a GitHub secret: `META_TOKEN_{SLUG}`
4. Push — the next scheduled run picks it up automatically

## CLI Commands

```bash
python -m brandfield run --period daily               # all clients
python -m brandfield run --period weekly --client acme_corp
python -m brandfield run --period daily --dry-run     # safe for development
python -m brandfield validate-config                  # validate all YAMLs
```

## GitHub Actions

Reports run automatically via GitHub Actions:

| Workflow | Schedule | Trigger |
|---|---|---|
| `daily_report.yml` | 08:00 UTC daily | Cron + manual |
| `weekly_report.yml` | 09:00 UTC Mondays | Cron + manual |

Both workflows commit generated `docs/` and `data/` files back to the repository, which triggers GitHub Pages auto-deployment.

## GitHub Pages Setup

1. Go to repository **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main`, Folder: `/docs`
4. Each client is available at `https://{org}.github.io/{repo}/{client_slug}/`

## WhatsApp Providers

Set `provider` in the client YAML to switch providers:

| Provider | Value | Notes |
|---|---|---|
| Meta WhatsApp Business | `meta` | Official API, requires verified business |
| Twilio | `twilio` | Simple setup, paid service |
| Evolution API | `evolution` | Open-source, popular in Brazil |
| None (dry-run) | `none` | Logs to stdout, no message sent |

## Project Structure

```
brandfield/          # Core Python package
  config/            # Pydantic config validation
  collectors/        # Meta Graph API data collection
  normalizers/       # Raw API → typed dataclasses
  storage/           # JSON file persistence
  renderers/         # Jinja2 + Chart.js HTML generation
  notifications/     # WhatsApp abstraction layer
  summary/           # Executive summary text builder
  pipeline.py        # Main orchestrator
  cli.py             # Click CLI entry point
clients/             # One YAML per client
data/                # Historical snapshots (committed to git)
docs/                # GitHub Pages output
tests/               # pytest test suite
.github/workflows/   # GitHub Actions automation
```

## Environment Variables

See `.env.example` for all required variables. In GitHub Actions, set them as repository secrets.
