"""JSON file-based storage for ClientSnapshot objects."""

import json
from datetime import date
from pathlib import Path
from typing import Optional

from brandfield.normalizers.models import ClientSnapshot
from brandfield.storage.base import BaseStorage

DATA_DIR = Path(__file__).parent.parent.parent / "data"


class JsonStore(BaseStorage):
    """
    Stores snapshots as JSON files under:
        {base_path}/{client_slug}/snapshot_{YYYY-MM-DD}.json

    Files use stable key order and 2-space indentation so git diffs
    are human-readable.
    """

    def __init__(self, base_path: Path = DATA_DIR):
        self.base_path = base_path

    def _client_dir(self, client_slug: str) -> Path:
        return self.base_path / client_slug

    def _snapshot_path(self, client_slug: str, report_date: date) -> Path:
        return self._client_dir(client_slug) / f"snapshot_{report_date.isoformat()}.json"

    def save(self, snapshot: ClientSnapshot) -> None:
        client_dir = self._client_dir(snapshot.client_slug)
        client_dir.mkdir(parents=True, exist_ok=True)

        path = self._snapshot_path(snapshot.client_slug, snapshot.report_date)
        with path.open("w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, indent=2, ensure_ascii=False)

    def load(self, client_slug: str, report_date: date) -> Optional[ClientSnapshot]:
        path = self._snapshot_path(client_slug, report_date)
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return ClientSnapshot.from_dict(data)

    def load_range(
        self, client_slug: str, start: date, end: date
    ) -> list[ClientSnapshot]:
        client_dir = self._client_dir(client_slug)
        if not client_dir.exists():
            return []

        snapshots = []
        for path in sorted(client_dir.glob("snapshot_*.json")):
            # Extract date from filename: snapshot_YYYY-MM-DD.json
            date_str = path.stem.replace("snapshot_", "")
            try:
                file_date = date.fromisoformat(date_str)
            except ValueError:
                continue

            if start <= file_date <= end:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                snapshots.append(ClientSnapshot.from_dict(data))

        return snapshots
