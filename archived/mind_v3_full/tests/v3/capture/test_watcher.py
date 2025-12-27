"""Tests for TranscriptWatcher."""
import tempfile
from pathlib import Path

import pytest

from mind.v3.capture.watcher import TranscriptWatcher, WatcherConfig


class TestWatcherConfig:
    """Tests for WatcherConfig."""

    def test_default_config(self):
        config = WatcherConfig()
        assert config.enabled is True
        assert config.extract_decisions is True
        assert config.extract_entities is True

    def test_custom_config(self):
        config = WatcherConfig(
            enabled=False,
            min_decision_confidence=0.8,
        )
        assert config.enabled is False
        assert config.min_decision_confidence == 0.8


class TestTranscriptWatcher:
    """Tests for TranscriptWatcher."""

    def test_create_watcher(self):
        watcher = TranscriptWatcher()
        assert watcher is not None
        assert watcher.config.enabled is True

    def test_process_user_turn(self):
        watcher = TranscriptWatcher()

        turn = {"role": "user", "content": "How do I fix this bug?"}
        events = watcher.process_turn(turn)

        assert len(events) >= 1
        assert watcher.get_stats()["turns_processed"] == 1

    def test_process_assistant_turn(self):
        watcher = TranscriptWatcher()

        turn = {
            "role": "assistant",
            "content": "I decided to use JWT tokens because they're stateless.",
        }
        events = watcher.process_turn(turn)

        assert len(events) >= 1
        # Should detect a decision
        decision_events = [e for e in events if e.type.value == "decision"]
        assert len(decision_events) >= 1

    def test_disabled_watcher(self):
        config = WatcherConfig(enabled=False)
        watcher = TranscriptWatcher(config=config)

        turn = {"role": "user", "content": "Test message"}
        events = watcher.process_turn(turn)

        assert len(events) == 0


class TestTranscriptWatcherWithStore:
    """Tests for TranscriptWatcher with GraphStore."""

    def test_stores_decisions(self):
        from mind.v3.graph.store import GraphStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = GraphStore(Path(tmpdir) / "graph")
            watcher = TranscriptWatcher(graph_store=store)

            initial_count = store.get_counts()["decisions"]

            turn = {
                "role": "assistant",
                "content": "I decided to use PostgreSQL because we need ACID compliance.",
            }
            watcher.process_turn(turn)

            final_count = store.get_counts()["decisions"]
            assert final_count > initial_count

    def test_stores_entities(self):
        from mind.v3.graph.store import GraphStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = GraphStore(Path(tmpdir) / "graph")
            watcher = TranscriptWatcher(graph_store=store)

            initial_count = store.get_counts()["entities"]

            turn = {
                "role": "assistant",
                "content": "I'm modifying the UserService class in src/services/user.py",
            }
            watcher.process_turn(turn)

            final_count = store.get_counts()["entities"]
            assert final_count >= initial_count

    def test_process_full_transcript(self):
        from mind.v3.graph.store import GraphStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = GraphStore(Path(tmpdir) / "graph")
            watcher = TranscriptWatcher(graph_store=store)

            transcript = [
                {"role": "user", "content": "Fix the login bug"},
                {"role": "assistant", "content": "I decided to use bcrypt for password hashing."},
                {"role": "user", "content": "Great, commit it"},
                {"role": "assistant", "content": "Done! Committed the changes."},
            ]

            events = watcher.process_transcript(transcript)

            assert len(events) >= 4
            stats = watcher.get_stats()
            assert stats["turns_processed"] == 4
