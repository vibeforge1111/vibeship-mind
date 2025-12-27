"""
Migration module for Mind v3.

Handles automatic migration of v2 data (MEMORY.md, SESSION.md) to v3 structured tables.
"""
from .manager import MigrationManager, MigrationStats, migrate_project

__all__ = ["MigrationManager", "MigrationStats", "migrate_project"]
