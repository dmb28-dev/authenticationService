# authenticationService

## Окружение (Poetry)

Виртуальное окружение создаётся **в каталоге проекта** (`.venv`), глобальный Python не используется.

```bash
poetry install          # зависимости в ./.venv
poetry run pytest       # тесты
poetry run uvicorn app.main:app --reload --app-dir src
```

Файл `poetry.toml` задаёт `virtualenvs.in-project = true`.

## База данных (опционально)

Если `APP_DATABASE_URL` не задан, HTTP-слой работает в **режиме заглушек** (как в задачах 1.x), без подключения к PostgreSQL.

При заданном `APP_DATABASE_URL` поднимается пул `asyncpg`, доступны миграции и seed:

```bash
export APP_DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
poetry run python -m app.cli migrate
poetry run python -m app.cli seed
```

См. также `db/README.md`.