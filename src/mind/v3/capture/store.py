"""
Event store for Mind v3.

Append-only storage for events using JSONL format.
Events are immutable once written.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Any, Callable

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


class SessionEventStore:
    """
    In-memory store for current session events.

    Provides fast access during session with optional persistence.
    Events are kept in memory for quick queries and can be persisted
    to disk at session end or periodically.
    """

    def __init__(self, project_path: Path):
        """
        Initialize session event store.

        Args:
            project_path: Root path of the project
        """
        self.project_path = Path(project_path)
        self.events: list[Event] = []
        self.session_id: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._processing_callback: Callable[[list[Event]], None] | None = None
        self._events_since_callback: int = 0

    def add(self, event: Event) -> None:
        """
        Add event to the session store.

        Sets the session_id on the event and triggers callback every 10 events.

        Args:
            event: Event to add
        """
        # Set session ID on the event
        event.session_id = self.session_id
        self.events.append(event)
        self._events_since_callback += 1

        # Trigger callback every 10 events
        if self._processing_callback and self._events_since_callback >= 10:
            self._processing_callback(self.events)
            self._events_since_callback = 0

    def get_events_since(self, timestamp: datetime) -> list[Event]:
        """
        Get events after a specific timestamp.

        Args:
            timestamp: Only return events after this timestamp

        Returns:
            List of events after the timestamp
        """
        return [e for e in self.events if e.timestamp > timestamp]

    def set_processing_callback(self, callback: Callable[[list[Event]], None]) -> None:
        """
        Set callback for batch processing.

        The callback is triggered every 10 events.

        Args:
            callback: Function to call with the list of events
        """
        self._processing_callback = callback

    def persist(self) -> Path:
        """
        Save session to .mind/v3/sessions/<session_id>.json.

        Returns:
            Path to the persisted session file
        """
        sessions_dir = self.project_path / ".mind" / "v3" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        session_file = sessions_dir / f"{self.session_id}.json"

        data = {
            "session_id": self.session_id,
            "start_time": self.events[0].timestamp.isoformat() if self.events else None,
            "end_time": self.events[-1].timestamp.isoformat() if self.events else None,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return session_file

    def clear(self) -> None:
        """Clear all events from the session."""
        self.events = []
        self._events_since_callback = 0
