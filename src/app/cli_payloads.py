"""CLI input/output types (RORO-style contracts for migrate and seed)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RunMigrationsInput:
    database_url: str
    migrations_dir: Path
    migration_table_name: str = "schema_migrations"


@dataclass(frozen=True)
class MigrationReport:
    applied: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedInput:
    database_url: str


@dataclass(frozen=True)
class SeedReport:
    roles_upserted: int = 0
    business_elements_upserted: int = 0
    access_rules_upserted: int = 0
    users_upserted: int = 0
    mock_documents_created: int = 0
    mock_reports_created: int = 0
    details: dict[str, int] = field(default_factory=dict)
