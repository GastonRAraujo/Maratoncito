import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_migration_bootstrap_and_rollback(tmp_path: Path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    database_file = tmp_path / "maratoncito.db"
    env = {**os.environ, "MARATONCITO_DATABASE_URL": f"sqlite:///{database_file}"}
    for revision in ("head", "base"):
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade" if revision == "head" else "downgrade", revision],
            cwd=backend_dir,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        with sqlite3.connect(database_file) as connection:
            names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert ("download_jobs" in names) is (revision == "head")
