"""
Migration manager for Mind v3.

Handles automatic migration of v2 data (MEMORY.md) to v3 structured tables,
ensuring no experiences are lost when upgrading.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..graph.store import GraphStore


@dataclass
class MigrationStats:
    """Statistics from a migration run."""

    memories_processed: int = 0
    decisions_added: int = 0
    entities_added: int = 0
    patterns_added: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_structured(self) -> int:
        """Total items added to structured tables."""
        return self.decisions_added + self.entities_added + self.patterns_added


@dataclass
class MemoryEntry:
    """A parsed memory entry from MEMORY.md."""

    content: str
    memory_type: str  # decision, learning, problem, context, etc.
    section: str  # Key, Context, Timeline, Gotchas, etc.
    timestamp: str | None = None

    @property
    def is_decision(self) -> bool:
        """Check if this looks like a decision."""
        return self.memory_type == "decision" or self._has_decision_keywords()

    def _has_decision_keywords(self) -> bool:
        """Check for decision keywords in content."""
        # Skip if it starts with learning indicators
        skip_prefixes = ["learned", "gotcha", "til", "problem", "fixed", "issue"]
        content_lower = self.content.lower().strip()
        for prefix in skip_prefixes:
            if content_lower.startswith(prefix):
                return False

        patterns = [
            r"\*\*Decided:\*\*",  # **Decided:** format
            r"\bdecided\s+to\b",
            r"\bdecided\s+on\b",
            r"\bdecided\s+NOT\s+to\b",
            r"\bchose\s+to\b",
            r"\bgoing\s+with\b",
            r"\bwent\s+with\b",
            r"\bsettled\s+on\b",
            r"\busing\b.*\binstead\b",
            r"\bKEY:\s*decided\b",  # KEY: decided format
        ]
        return any(re.search(p, self.content, re.IGNORECASE) for p in patterns)


class MemoryParser:
    """Parses MEMORY.md into structured entries."""

    # Section markers in MEMORY.md
    SECTIONS = {
        "## Key": "key_decisions",
        "## Context": "context",
        "## Timeline": "timeline",
        "## Gotchas": "gotchas",
        "## Stack": "stack",
        "## Preferences": "preferences",
    }

    # Inline markers for typed entries
    INLINE_MARKERS = {
        "**Decided:**": "decision",
        "**Problem:**": "problem",
        "**Learned:**": "learning",
        "**Fixed:**": "progress",
        "**Implemented:**": "progress",
        "**Researched": "context",
        "decided to": "decision",
        "decided on": "decision",
        "decided NOT to": "decision",
        "KEY: decided": "decision",
        "Going with": "decision",
        "learned that": "learning",
        "learned:": "learning",
        "gotcha:": "learning",
        "TIL:": "learning",
        "problem:": "problem",
        "fixed:": "progress",
        "fixed by": "progress",
    }

    def parse(self, content: str) -> list[MemoryEntry]:
        """
        Parse MEMORY.md content into structured entries.

        Args:
            content: Raw MEMORY.md content

        Returns:
            List of MemoryEntry objects
        """
        entries = []
        current_section = "general"
        current_date = None

        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Check for section headers
            for marker, section_name in self.SECTIONS.items():
                if line.startswith(marker):
                    current_section = section_name
                    i += 1
                    continue

            # Check for date headers (## 2025-12-13 ...)
            date_match = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})", line)
            if date_match:
                current_date = date_match.group(1)
                i += 1
                continue

            # Parse inline typed entries (**Decided:**, **Problem:**, etc.)
            for marker, mem_type in self.INLINE_MARKERS.items():
                if marker in line:
                    # Extract content after marker
                    if marker.startswith("**"):
                        # Handle **Marker:** format
                        entry_content = line.split(marker, 1)[-1].strip()
                    else:
                        # Handle lowercase markers - include the whole line
                        entry_content = line.strip()

                    if entry_content:
                        entries.append(MemoryEntry(
                            content=entry_content,
                            memory_type=mem_type,
                            section=current_section,
                            timestamp=current_date,
                        ))
                    break  # Only match first marker

            # Parse list items (most memories are bullet points)
            if line.startswith("- "):
                entry_content = line[2:].strip()

                # Check for multi-line entries (indented continuation)
                while i + 1 < len(lines) and lines[i + 1].startswith("  "):
                    i += 1
                    entry_content += " " + lines[i].strip()

                if entry_content:
                    entry = self._parse_entry(entry_content, current_section)
                    if entry:
                        entry.timestamp = current_date
                        entries.append(entry)

            # Parse dated entries (Timeline format with **)
            elif re.match(r"\*\*\d{4}-\d{2}-\d{2}", line):
                # Extract date and content
                dated_match = re.match(r"\*\*(\d{4}-\d{2}-\d{2})\*\*:?\s*(.*)", line)
                if dated_match:
                    timestamp = dated_match.group(1)
                    entry_content = dated_match.group(2).strip()

                    # Collect continuation lines
                    while i + 1 < len(lines) and not lines[i + 1].startswith("**") and lines[i + 1].strip():
                        i += 1
                        entry_content += " " + lines[i].strip()

                    if entry_content:
                        entry = self._parse_entry(entry_content, current_section)
                        if entry:
                            entry.timestamp = timestamp
                            entries.append(entry)

            i += 1

        return entries

    def _parse_entry(self, content: str, section: str) -> MemoryEntry | None:
        """Parse a single entry."""
        if not content or len(content) < 5:
            return None

        # Determine memory type based on content patterns and section
        memory_type = self._infer_type(content, section)

        return MemoryEntry(
            content=content,
            memory_type=memory_type,
            section=section,
        )

    def _infer_type(self, content: str, section: str) -> str:
        """Infer memory type from content and section."""
        content_lower = content.lower()

        # Section-based inference
        if section == "key_decisions":
            return "decision"
        elif section == "gotchas":
            return "learning"
        elif section == "preferences":
            return "preference"
        elif section == "stack":
            return "context"

        # Content-based inference
        if any(kw in content_lower for kw in ["decided", "chose", "going with", "using", "went with"]):
            return "decision"
        elif any(kw in content_lower for kw in ["learned", "discovered", "realized", "turns out", "til", "gotcha"]):
            return "learning"
        elif any(kw in content_lower for kw in ["problem", "issue", "bug", "error", "failed", "broken"]):
            return "problem"
        elif any(kw in content_lower for kw in ["fixed", "resolved", "solved", "working"]):
            return "progress"
        elif any(kw in content_lower for kw in ["prefer", "like to", "always use", "favor"]):
            return "preference"

        return "general"


class MigrationManager:
    """
    Manages migration of v2 data to v3 structured tables.

    This runs automatically when v3 initializes for the first time,
    ensuring no prior experiences are lost during upgrade.
    """

    MIGRATION_MARKER = ".v3_migrated"

    def __init__(self, project_path: Path, graph_store: "GraphStore"):
        """
        Initialize migration manager.

        Args:
            project_path: Path to project root
            graph_store: GraphStore instance for v3 data
        """
        self.project_path = Path(project_path)
        self.store = graph_store
        self.parser = MemoryParser()
        self.mind_dir = self.project_path / ".mind"

    def needs_migration(self) -> bool:
        """
        Check if migration is needed.

        Returns True if:
        - MEMORY.md exists
        - Migration hasn't been run yet (no marker file)
        - Or structured tables are empty despite having memories
        """
        memory_file = self.mind_dir / "MEMORY.md"
        marker_file = self.mind_dir / "v3" / self.MIGRATION_MARKER

        if not memory_file.exists():
            return False

        if marker_file.exists():
            # Already migrated - but check if we need to sync new content
            return self._has_new_content()

        return True

    def _has_new_content(self) -> bool:
        """Check if MEMORY.md has new content since last migration."""
        memory_file = self.mind_dir / "MEMORY.md"
        marker_file = self.mind_dir / "v3" / self.MIGRATION_MARKER

        if not memory_file.exists() or not marker_file.exists():
            return True

        # Compare file modification times
        try:
            memory_mtime = memory_file.stat().st_mtime
            marker_mtime = marker_file.stat().st_mtime

            # If MEMORY.md is newer than migration marker, we have new content
            if memory_mtime > marker_mtime:
                return True
        except OSError:
            return True

        # Also check if structured tables are mostly empty
        memory_count = self.store.memory_count()
        counts = self.store.get_counts()

        if memory_count > 0:
            structured_count = counts.get("decisions", 0) + counts.get("entities", 0) + counts.get("patterns", 0)
            # If structured tables are mostly empty, we should re-process
            if structured_count < memory_count // 10:  # Less than 10% extraction rate
                return True

        return False

    def sync_incremental(self) -> MigrationStats:
        """
        Incrementally sync new content from MEMORY.md to v3.

        Unlike full migration, this:
        - Only processes entries not already in v3
        - Uses content-based deduplication
        - Updates the sync marker timestamp

        Returns:
            MigrationStats with results
        """
        stats = MigrationStats()

        memory_file = self.mind_dir / "MEMORY.md"
        if not memory_file.exists():
            return stats

        # Import extractors
        from ..intelligence.local import (
            extract_decisions_local,
            extract_entities_local,
            extract_patterns_local,
        )

        try:
            content = memory_file.read_text(encoding="utf-8")
            entries = self.parser.parse(content)

            # Track what we've already added
            def normalize_key(text: str) -> str:
                """Normalize text for deduplication comparison."""
                text = text.lower().strip()
                for prefix in ["decided to ", "decided on ", "key: decided to ", "key: "]:
                    if text.startswith(prefix):
                        text = text[len(prefix):]
                return text[:80]

            existing_decisions = {normalize_key(d["action"]) for d in self.store.get_all_decisions()}
            existing_patterns = {normalize_key(p["description"]) for p in self.store.get_all_patterns()}

            for entry in entries:
                stats.memories_processed += 1

                try:
                    # Skip if memory already exists (incremental)
                    if self.store.memory_exists(entry.content):
                        continue

                    # Add new memory
                    self.store.add_memory(entry.content, entry.memory_type)

                    # Extract and store decisions
                    if entry.is_decision or entry.memory_type == "decision":
                        action = self._clean_decision_text(entry.content)
                        action_key = normalize_key(action)

                        if action and action_key not in existing_decisions:
                            reasoning = ""
                            for kw in ["because", "since", "due to", "-"]:
                                if kw in entry.content.lower():
                                    parts = entry.content.split(kw, 1)
                                    if len(parts) > 1:
                                        reasoning = parts[1].strip()
                                        break

                            self.store.add_decision({
                                "action": action,
                                "reasoning": reasoning,
                                "alternatives": [],
                                "confidence": 0.7 if entry.memory_type == "decision" else 0.5,
                                "timestamp": entry.timestamp or datetime.now(timezone.utc).isoformat(),
                            })
                            existing_decisions.add(action_key)
                            stats.decisions_added += 1

                    # Extract entities
                    entity_result = extract_entities_local(entry.content)
                    for entity in entity_result.get("content", {}).get("entities", []):
                        self.store.add_entity({
                            "name": entity.get("name", ""),
                            "type": entity.get("type", "unknown"),
                            "description": f"From: {entry.section}",
                            "properties": {"source": "incremental_sync", "section": entry.section},
                        })
                        stats.entities_added += 1

                    # Extract patterns from preferences
                    if entry.memory_type in ("preference", "learning") or entry.section == "preferences":
                        pattern_result = extract_patterns_local(entry.content)
                        for pattern in pattern_result.get("content", {}).get("patterns", []):
                            desc = pattern.get("description", "")
                            desc_key = normalize_key(desc)
                            if desc and desc_key not in existing_patterns:
                                self.store.add_pattern({
                                    "description": desc,
                                    "pattern_type": pattern.get("pattern_type", "preference"),
                                    "confidence": pattern.get("confidence", 0.5),
                                    "evidence_count": 1,
                                })
                                existing_patterns.add(desc_key)
                                stats.patterns_added += 1

                except Exception as e:
                    stats.errors.append(f"Error syncing '{entry.content[:50]}...': {str(e)}")

            # Update sync marker timestamp
            self._write_migration_marker(stats)

        except Exception as e:
            stats.errors.append(f"Incremental sync failed: {str(e)}")

        return stats

    def migrate(self, force: bool = False) -> MigrationStats:
        """
        Run migration from MEMORY.md to v3 structured tables.

        Args:
            force: Force re-migration even if already done

        Returns:
            MigrationStats with results
        """
        stats = MigrationStats()

        memory_file = self.mind_dir / "MEMORY.md"
        if not memory_file.exists():
            return stats

        # Handle force flag - clear existing data and marker
        if force:
            marker_file = self.mind_dir / "v3" / self.MIGRATION_MARKER
            if marker_file.exists():
                marker_file.unlink()

            # Clear structured tables for fresh migration
            for table_name in ["decisions", "patterns"]:
                try:
                    table = self.store.db.open_table(table_name)
                    if table.count_rows() > 0:
                        table.delete("id IS NOT NULL")
                except Exception:
                    logger.debug("Table %s doesn't exist yet, skipping clear", table_name)

        # Import extractors
        from ..intelligence.local import (
            extract_decisions_local,
            extract_entities_local,
            extract_patterns_local,
        )

        try:
            content = memory_file.read_text(encoding="utf-8")
            entries = self.parser.parse(content)

            # Track what we've already added to avoid duplicates
            # Normalize keys for better deduplication
            def normalize_key(text: str) -> str:
                """Normalize text for deduplication comparison."""
                text = text.lower().strip()
                # Remove common prefixes for comparison
                for prefix in ["decided to ", "decided on ", "key: decided to ", "key: "]:
                    if text.startswith(prefix):
                        text = text[len(prefix):]
                return text[:80]  # Use first 80 chars for matching

            existing_decisions = {normalize_key(d["action"]) for d in self.store.get_all_decisions()}
            existing_patterns = {normalize_key(p["description"]) for p in self.store.get_all_patterns()}

            for entry in entries:
                stats.memories_processed += 1

                try:
                    # Add to memories table if not exists
                    if not self.store.memory_exists(entry.content):
                        self.store.add_memory(entry.content, entry.memory_type)

                    # Store decisions - both from type detection and content patterns
                    if entry.is_decision or entry.memory_type == "decision":
                        # Clean up the decision text
                        action = self._clean_decision_text(entry.content)
                        action_key = normalize_key(action)

                        if action and action_key not in existing_decisions:
                            # Try to extract reasoning
                            reasoning = ""
                            for kw in ["because", "since", "due to", "-"]:
                                if kw in entry.content.lower():
                                    parts = entry.content.split(kw, 1)
                                    if len(parts) > 1:
                                        reasoning = parts[1].strip()
                                        break

                            self.store.add_decision({
                                "action": action,
                                "reasoning": reasoning,
                                "alternatives": [],
                                "confidence": 0.7 if entry.memory_type == "decision" else 0.5,
                                "timestamp": entry.timestamp or datetime.now(timezone.utc).isoformat(),
                            })
                            existing_decisions.add(action_key)
                            stats.decisions_added += 1

                        # Also try the extractor for additional decisions
                        decision_result = extract_decisions_local(entry.content)
                        for decision in decision_result.get("content", {}).get("decisions", []):
                            dec_action = decision.get("action", "")
                            dec_key = normalize_key(dec_action)
                            if dec_action and dec_key not in existing_decisions:
                                self.store.add_decision({
                                    "action": dec_action,
                                    "reasoning": decision.get("reasoning", ""),
                                    "alternatives": decision.get("alternatives", []),
                                    "confidence": decision.get("confidence", 0.5),
                                    "timestamp": entry.timestamp or datetime.now(timezone.utc).isoformat(),
                                })
                                existing_decisions.add(dec_key)
                                stats.decisions_added += 1

                    # Extract entities from all entries
                    entity_result = extract_entities_local(entry.content)
                    for entity in entity_result.get("content", {}).get("entities", []):
                        self.store.add_entity({
                            "name": entity.get("name", ""),
                            "type": entity.get("type", "unknown"),
                            "description": f"From: {entry.section}",
                            "properties": {"source": "migration", "section": entry.section},
                        })
                        stats.entities_added += 1

                    # Extract patterns from preference/habit entries
                    if entry.memory_type in ("preference", "learning") or entry.section == "preferences":
                        pattern_result = extract_patterns_local(entry.content)
                        for pattern in pattern_result.get("content", {}).get("patterns", []):
                            desc = pattern.get("description", "")
                            desc_key = normalize_key(desc)
                            if desc and desc_key not in existing_patterns:
                                self.store.add_pattern({
                                    "description": pattern.get("description", ""),
                                    "pattern_type": pattern.get("pattern_type", "preference"),
                                    "confidence": pattern.get("confidence", 0.5),
                                    "evidence_count": 1,
                                })
                                existing_patterns.add(desc_key)
                                stats.patterns_added += 1

                except Exception as e:
                    stats.errors.append(f"Error processing '{entry.content[:50]}...': {str(e)}")

            # Mark migration complete
            self._write_migration_marker(stats)

        except Exception as e:
            stats.errors.append(f"Migration failed: {str(e)}")

        return stats

    def _clean_decision_text(self, text: str) -> str:
        """Clean up decision text by removing markdown and prefixes."""
        result = text
        # Remove common prefixes
        prefixes_to_remove = [
            "**Decided:**",
            "**decided:**",
            "KEY: decided",
            "KEY:",
            "decided to",
            "decided on",
            "decided NOT to",
            "Going with",
        ]
        for prefix in prefixes_to_remove:
            if result.lower().startswith(prefix.lower()):
                result = result[len(prefix):].strip()

        # Remove markdown formatting
        result = re.sub(r"\*\*([^*]+)\*\*", r"\1", result)  # **bold**
        result = re.sub(r"\*([^*]+)\*", r"\1", result)  # *italic*

        return result.strip()

    def _write_migration_marker(self, stats: MigrationStats) -> None:
        """Write marker file indicating migration is complete."""
        marker_dir = self.mind_dir / "v3"
        marker_dir.mkdir(parents=True, exist_ok=True)

        marker_file = marker_dir / self.MIGRATION_MARKER
        marker_file.write_text(
            f"Migrated at: {datetime.now(timezone.utc).isoformat()}\n"
            f"Memories processed: {stats.memories_processed}\n"
            f"Decisions added: {stats.decisions_added}\n"
            f"Entities added: {stats.entities_added}\n"
            f"Patterns added: {stats.patterns_added}\n"
            f"Errors: {len(stats.errors)}\n"
        )


def migrate_project(project_path: Path, force: bool = False) -> MigrationStats:
    """
    Convenience function to migrate a project to v3.

    Args:
        project_path: Path to project root
        force: Force re-migration

    Returns:
        MigrationStats with results
    """
    from ..graph.store import GraphStore

    graph_path = project_path / ".mind" / "v3" / "graph"
    store = GraphStore(graph_path)

    manager = MigrationManager(project_path, store)
    return manager.migrate(force=force)
