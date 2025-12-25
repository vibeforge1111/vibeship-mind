"""
Event store for Mind v3.

Append-only storage for events using JSONL format.
Events are immutable once written.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Any

from .events import Event


class EventStore:
    """
    Append-only event store using JSONL files.

    Events are stored in daily files: YYYY-MM-DD.jsonl
    This enables efficient date-range queries and archival.
    """

    def __init__(self, path: Path):
        """
        Initialize event store.

        Args:
            path: Directory to store event files
        """
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def _get_file_for_date(self, dt: datetime) -> Path:
        """Get the JSONL file path for a given date."""
        return self.path / f"{dt.strftime('%Y-%m-%d')}.jsonl"

    def _get_current_file(self) -> Path:
        """Get the JSONL file for today."""
        return self._get_file_for_date(datetime.now(timezone.utc))

    def append(self, event: Event) -> None:
        """
        Append an event to the store.

        Args:
            event: Event to append
        """
        file_path = self._get_file_for_date(event.timestamp)

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def iter_events(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        event_types: list[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """
        Iterate over events in the store.

        Args:
            since: Only return events after this timestamp
            until: Only return events before this timestamp
            event_types: Only return events of these types

        Yields:
            Event dictionaries
        """
        # Get all JSONL files, sorted by date
        files = sorted(self.path.glob("*.jsonl"))

        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    event = json.loads(line)

                    # Parse timestamp for filtering
                    event_time = datetime.fromisoformat(event["timestamp"])

                    # Apply filters
                    if since and event_time <= since:
                        continue
                    if until and event_time >= until:
                        continue
                    if event_types and event["type"] not in event_types:
                        continue

                    yield event

    def count(self) -> int:
        """Return total number of events in store."""
        total = 0
        for file_path in self.path.glob("*.jsonl"):
            with open(file_path, "r", encoding="utf-8") as f:
                total += sum(1 for line in f if line.strip())
        return total

    def get_latest(self, n: int = 10) -> list[dict[str, Any]]:
        """
        Get the N most recent events.

        Args:
            n: Number of events to return

        Returns:
            List of event dictionaries, most recent first
        """
        events = list(self.iter_events())
        return events[-n:][::-1]

    def clear(self) -> None:
        """Clear all events from the store. Use with caution."""
        for file_path in self.path.glob("*.jsonl"):
            file_path.unlink()
