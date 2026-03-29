"""Click CLI entry point for BrandField Reporting."""

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

# Load .env before any other imports that read env vars
load_dotenv()

from brandfield.config.loader import (
    ConfigError,
    load_all_clients,
    load_client_config,
    validate_credentials,
)
from brandfield.pipeline import ReportPipeline
from brandfield.renderers.html_renderer import DOCS_DIR, HtmlRenderer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

CLIENTS_DIR = Path(__file__).parent.parent / "clients"


@click.group()
def cli():
    """BrandField automated reporting system."""


@cli.command()
@click.option(
    "--period",
    type=click.Choice(["daily", "weekly"]),
    default="daily",
    show_default=True,
    help="Report period.",
)
@click.option(
    "--client",
    "client_slug",
    default=None,
    help="Run for a single client slug. Omit to run all clients.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Use fixture data instead of real APIs. No WhatsApp messages sent.",
)
def run(period: str, client_slug: str | None, dry_run: bool):
    """Run the reporting pipeline for one or all clients."""
    if dry_run:
        click.echo("[dry-run] Using fixture data. No real API calls or WhatsApp sends.")

    # Load client configs
    if client_slug:
        config_path = CLIENTS_DIR / f"{client_slug}.yml"
        try:
            clients = [load_client_config(config_path)]
        except ConfigError as e:
            click.echo(f"Error loading config: {e}", err=True)
            sys.exit(1)
    else:
        clients = load_all_clients(CLIENTS_DIR)
        if not clients:
            click.echo(
                f"No client configs found in {CLIENTS_DIR}. "
                "Create a YAML file to get started.",
                err=True,
            )
            sys.exit(1)

    click.echo(f"Running {period} report for {len(clients)} client(s)...")

    # Validate credentials before running (skip in dry-run)
    failed_validation = []
    for client in clients:
        try:
            validate_credentials(client, dry_run=dry_run)
        except ConfigError as e:
            click.echo(f"  [SKIP] {client.slug}: {e}", err=True)
            failed_validation.append(client.slug)

    clients = [c for c in clients if c.slug not in failed_validation]

    # Run pipeline
    all_results = []
    for client in clients:
        click.echo(f"  → {client.slug} ({client.display_name})...")
        pipeline = ReportPipeline(client, dry_run=dry_run)
        result = pipeline.run(period=period)
        all_results.append(result)

        if result.success:
            status = "OK"
            if result.report_path:
                status += f" → {result.report_path}"
            if result.notification_sent:
                status += " [WhatsApp sent]"
            click.echo(f"     {status}")
        else:
            click.echo(f"     FAILED: {'; '.join(result.errors)}", err=True)

    # Update index page
    if clients:
        renderer = HtmlRenderer()
        all_loaded_clients = load_all_clients(CLIENTS_DIR)
        renderer.write_index(all_loaded_clients, docs_dir=DOCS_DIR)
        click.echo(f"Index updated: {DOCS_DIR / 'index.html'}")

    # Summary
    n_ok = sum(1 for r in all_results if r.success)
    n_fail = len(all_results) - n_ok
    click.echo(f"\nDone: {n_ok} succeeded, {n_fail} failed.")

    if n_fail > 0:
        sys.exit(1)


@cli.command("validate-config")
def validate_config():
    """Validate all client YAML configurations."""
    clients_dir = CLIENTS_DIR
    yaml_files = sorted(
        p for p in clients_dir.glob("*.yml") if not p.stem.startswith("_")
    )

    if not yaml_files:
        click.echo(f"No client configs found in {clients_dir}.")
        return

    errors = []
    for path in yaml_files:
        try:
            client = load_client_config(path)
            click.echo(f"  OK  {path.name}  →  {client.display_name}")
        except ConfigError as e:
            click.echo(f"  ERR {path.name}:\n      {e}", err=True)
            errors.append(path.name)

    if errors:
        click.echo(f"\n{len(errors)} config(s) have errors.", err=True)
        sys.exit(1)
    else:
        click.echo(f"\nAll {len(yaml_files)} config(s) are valid.")


if __name__ == "__main__":
    cli()
