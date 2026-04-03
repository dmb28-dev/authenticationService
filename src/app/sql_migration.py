"""Split raw SQL migration files into executable statements."""

from __future__ import annotations

from pathlib import Path


def split_sql_statements(sql_text: str) -> list[str]:
    lines: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    buf = "\n".join(lines)
    statements: list[str] = []
    for raw in buf.split(";"):
        stmt = raw.strip()
        if stmt:
            statements.append(stmt)
    return statements


def list_migration_files(migrations_dir: Path) -> list[Path]:
    files = sorted(migrations_dir.glob("*.sql"))
    return [p for p in files if p.is_file()]
