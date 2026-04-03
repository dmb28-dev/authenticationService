# Миграции PostgreSQL

SQL-файлы в `db/migrations/` применяются по имени в лексикографическом порядке. Версия фиксируется в таблице `schema_migrations` (имя задаётся `APP_MIGRATION_TABLE_NAME`).

Запуск из корня проекта (нужен `APP_DATABASE_URL`):

```bash
poetry run python -m app.cli migrate
poetry run python -m app.cli run-migrations
poetry run python -m app.cli seed
poetry run python -m app.cli seed-data
poetry run python -m app.cli create-dev-data
```
