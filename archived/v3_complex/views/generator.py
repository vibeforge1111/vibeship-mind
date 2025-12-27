"""Generate human-readable markdown views from graph data."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..graph.store import GraphStore


class ViewGenerator:
    """
    Generates markdown views from graph store.

    Creates human-readable files:
    - DECISIONS.md: All recorded decisions
    - PATTERNS.md: Detected patterns
    - POLICIES.md: Active and inactive policies
    """

    def __init__(self, graph_store: "GraphStore", output_dir: Path):
        """
        Initialize view generator.

        Args:
            graph_store: GraphStore to read data from
            output_dir: Directory to write view files to
        """
        self.graph = graph_store
        self.output_dir = Path(output_dir)

    def generate_decisions_view(self) -> Path:
        """
        Generate DECISIONS.md with all decisions.

        Returns:
            Path to generated file
        """
        decisions = self.graph.get_all_decisions()

        lines = [
            "# Decisions",
            "",
            f"*Generated: {datetime.now().isoformat()}*",
            "",
        ]

        if not decisions:
            lines.append("*No decisions recorded yet.*")
        else:
            for dec in decisions:
                action = dec.get("action", "Unknown")
                reasoning = dec.get("reasoning", "N/A")
                confidence = dec.get("confidence", 0)
                alternatives = dec.get("alternatives", [])

                lines.extend([
                    f"## {action}",
                    "",
                    f"**Reasoning:** {reasoning}",
                    "",
                    f"**Confidence:** {confidence:.0%}",
                    "",
                ])

                if alternatives:
                    lines.append("**Alternatives considered:**")
                    for alt in alternatives:
                        lines.append(f"- {alt}")
                    lines.append("")

                lines.extend([
                    "---",
                    "",
                ])

        path = self.output_dir / "DECISIONS.md"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def generate_patterns_view(self) -> Path:
        """
        Generate PATTERNS.md with all patterns.

        Returns:
            Path to generated file
        """
        patterns = self.graph.get_all_patterns()

        lines = [
            "# Patterns",
            "",
            f"*Generated: {datetime.now().isoformat()}*",
            "",
        ]

        if not patterns:
            lines.append("*No patterns detected yet.*")
        else:
            # Group patterns by type
            by_type: dict[str, list] = {}
            for pat in patterns:
                pat_type = pat.get("pattern_type", "general")
                if pat_type not in by_type:
                    by_type[pat_type] = []
                by_type[pat_type].append(pat)

            for pat_type, pats in sorted(by_type.items()):
                lines.extend([
                    f"## {pat_type.title()} Patterns",
                    "",
                ])

                for pat in pats:
                    description = pat.get("description", "Unknown")
                    confidence = pat.get("confidence", 0)
                    evidence = pat.get("evidence_count", 0)

                    lines.extend([
                        f"### {description}",
                        "",
                        f"**Confidence:** {confidence:.0%}",
                        f"**Evidence:** {evidence} occurrences",
                        "",
                    ])

                lines.extend([
                    "---",
                    "",
                ])

        path = self.output_dir / "PATTERNS.md"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def generate_policies_view(self) -> Path:
        """
        Generate POLICIES.md with all policies.

        Returns:
            Path to generated file
        """
        policies = self.graph.search_policies("", limit=100)

        lines = [
            "# Policies",
            "",
            f"*Generated: {datetime.now().isoformat()}*",
            "",
        ]

        if not policies:
            lines.append("*No policies defined yet.*")
        else:
            # Separate active and inactive
            active = [p for p in policies if p.get("active", True)]
            inactive = [p for p in policies if not p.get("active", True)]

            if active:
                lines.extend([
                    "## Active Policies",
                    "",
                ])

                for pol in active:
                    rule = pol.get("rule", "Unknown")
                    scope = pol.get("scope", "project")
                    source = pol.get("source", "inferred")

                    lines.extend([
                        f"### {rule}",
                        "",
                        f"**Scope:** {scope}",
                        f"**Source:** {source}",
                        "",
                    ])

            if inactive:
                lines.extend([
                    "## Inactive Policies",
                    "",
                ])

                for pol in inactive:
                    rule = pol.get("rule", "Unknown")
                    scope = pol.get("scope", "project")
                    source = pol.get("source", "inferred")

                    lines.extend([
                        f"### ~~{rule}~~",
                        "",
                        f"**Scope:** {scope}",
                        f"**Source:** {source}",
                        "",
                    ])

            lines.extend([
                "---",
                "",
            ])

        path = self.output_dir / "POLICIES.md"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def generate_all(self) -> list[Path]:
        """
        Generate all views.

        Returns:
            List of paths to generated files
        """
        return [
            self.generate_decisions_view(),
            self.generate_patterns_view(),
            self.generate_policies_view(),
        ]
