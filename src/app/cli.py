"""CLI: apply SQL migrations and load seed data."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg
from asyncpg.exceptions import UndefinedTableError

from app.cli_payloads import MigrationReport, RunMigrationsInput, SeedInput, SeedReport
from app.core.config import load_settings
from app.seeds import demo_users_seed, mock_resources_seed, reference_seed
from app.sql_migration import list_migration_files, split_sql_statements


def _migration_table_sql_ident(name: str) -> str:
    if not name:
        msg = "migration_table_name must be non-empty"
        raise ValueError(msg)
    for ch in name:
        if not (ch.isascii() and (ch.isalnum() or ch == "_")):
            msg = "migration_table_name must be alphanumeric ASCII or underscore"
            raise ValueError(msg)
    if name[0].isdigit():
        msg = "migration_table_name must not start with a digit"
        raise ValueError(msg)
    return name


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


async def run_migrations(payload: RunMigrationsInput) -> MigrationReport:
    table = _migration_table_sql_ident(payload.migration_table_name)
    files = list_migration_files(payload.migrations_dir)
    applied: list[str] = []
    conn = await asyncpg.connect(payload.database_url)
    try:
        try:
            rows = await conn.fetch(f"SELECT version FROM {table}")
            existing = {r["version"] for r in rows}
        except UndefinedTableError:
            existing = set()
        for path in files:
            version = path.name
            if version in existing:
                continue
            sql_text = path.read_text(encoding="utf-8")
            stmts = split_sql_statements(sql_text)
            async with conn.transaction():
                for stmt in stmts:
                    await conn.execute(stmt)
                await conn.execute(
                    f"INSERT INTO {table} (version) VALUES ($1)",
                    version,
                )
            applied.append(version)
            existing.add(version)
    finally:
        await conn.close()
    return MigrationReport(applied=tuple(applied))


async def seed_data(payload: SeedInput) -> SeedReport:
    conn = await asyncpg.connect(payload.database_url)
    try:
        async with conn.transaction():
            ref = await reference_seed.run(conn)
            users = await demo_users_seed.run(conn)
            mocks = await mock_resources_seed.run(conn)
    finally:
        await conn.close()
    details = {**ref, **users, **mocks}
    return SeedReport(
        roles_upserted=ref.get("roles_upserted", 0),
        business_elements_upserted=ref.get("business_elements_upserted", 0),
        access_rules_upserted=ref.get("access_rules_upserted", 0),
        users_upserted=users.get("users_upserted", 0),
        mock_documents_created=mocks.get("mock_documents_created", 0),
        mock_reports_created=mocks.get("mock_reports_created", 0),
        details=details,
    )


async def create_dev_data(payload: SeedInput) -> SeedReport:
    return await seed_data(payload)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    common_db = argparse.ArgumentParser(add_help=False)
    common_db.add_argument("--database-url", default=None, dest="database_url")

    migrate_parent = argparse.ArgumentParser(add_help=False)
    migrate_parent.add_argument(
        "--migrations-dir",
        type=Path,
        default=None,
        dest="migrations_dir",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", parents=[common_db, migrate_parent])
    sub.add_parser("run-migrations", parents=[common_db, migrate_parent])
    sub.add_parser("seed", parents=[common_db])
    sub.add_parser("seed-data", parents=[common_db])
    sub.add_parser("create-dev-data", parents=[common_db])

    return parser


async def _async_main(argv: list[str] | None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = load_settings()
    database_url = args.database_url or settings.database_url
    if not database_url:
        sys.stderr.write("Set APP_DATABASE_URL or pass --database-url.\n")
        return 2

    if args.command in ("migrate", "run-migrations"):
        migrations_dir = args.migrations_dir or (project_root() / "db" / "migrations")
        report = await run_migrations(
            RunMigrationsInput(
                database_url=database_url,
                migrations_dir=migrations_dir,
                migration_table_name=settings.migration_table_name,
            )
        )
        for v in report.applied:
            print(f"applied: {v}")
        if not report.applied:
            print("no pending migrations")
        return 0

    if args.command in ("seed", "seed-data", "create-dev-data"):
        report = await seed_data(SeedInput(database_url=database_url))
        print(
            "seed:",
            f"roles={report.roles_upserted}",
            f"be={report.business_elements_upserted}",
            f"rules={report.access_rules_upserted}",
            f"users={report.users_upserted}",
            f"docs={report.mock_documents_created}",
            f"reports={report.mock_reports_created}",
        )
        return 0

    return 1


def main() -> None:
    raise SystemExit(asyncio.run(_async_main(sys.argv[1:])))


if __name__ == "__main__":
    main()
