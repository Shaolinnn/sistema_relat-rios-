"""Abstract base class for snapshot storage."""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from brandfield.normalizers.models import ClientSnapshot


class BaseStorage(ABC):

    @abstractmethod
    def save(self, snapshot: ClientSnapshot) -> None:
        """Persist a snapshot. Idempotent — safe to call multiple times for the same date."""

    @abstractmethod
    def load(self, client_slug: str, report_date: date) -> Optional[ClientSnapshot]:
        """Return the snapshot for a given client and date, or None if not found."""

    @abstractmethod
    def load_range(
        self, client_slug: str, start: date, end: date
    ) -> list[ClientSnapshot]:
        """Return all snapshots in [start, end] inclusive, sorted by date ascending."""
