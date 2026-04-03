"""TC-UNIT-01: migration file ordering and SQL splitting."""

from pathlib import Path

from app.sql_migration import list_migration_files, split_sql_statements


def test_split_sql_statements_strips_comments_and_splits():
    sql = """
    -- header
    CREATE TABLE a (id INT);
    CREATE TABLE b (id INT);
    """
    stmts = split_sql_statements(sql)
    assert stmts == ["CREATE TABLE a (id INT)", "CREATE TABLE b (id INT)"]


def test_list_migration_files_lexicographic(tmp_path: Path):
    (tmp_path / "0002_second.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "0001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    files = list_migration_files(tmp_path)
    assert [p.name for p in files] == ["0001_first.sql", "0002_second.sql"]
