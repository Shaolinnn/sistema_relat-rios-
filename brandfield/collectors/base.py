"""Abstract base class for all data collectors."""

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures"


class CollectorError(Exception):
    """Raised when a collector fails to retrieve data."""


class BaseCollector(ABC):
    """
    Contract for all collectors.

    In dry_run mode, load_fixture() returns pre-recorded API responses from
    tests/fixtures/ instead of making real API calls.
    """

    def __init__(self, credentials: dict, dry_run: bool = False):
        self.credentials = credentials
        self.dry_run = dry_run

    @abstractmethod
    def collect(self, start_date: date, end_date: date) -> list[dict]:
        """
        Fetch data from the source API.

        Returns a list of raw dicts (one per record, e.g. one per campaign).
        Raises CollectorError on auth failure, rate limits, or missing permissions.
        """

    def load_fixture(self, filename: str) -> list[dict]:
        """Load a JSON fixture file from tests/fixtures/."""
        import json

        path = FIXTURES_DIR / filename
        if not path.exists():
            raise CollectorError(
                f"Fixture file not found: {path}. "
                "Create it to use dry-run mode, or run against the real API."
            )
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
