from pathlib import Path
import sqlite3

from matanyone2.webapp.runtime_paths import ensure_parent_dir


def init_database(database_path: Path) -> None:
    ensure_parent_dir(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                source_video_path TEXT NOT NULL,
                mask_path TEXT NOT NULL,
                template_frame_index INTEGER NOT NULL,
                params_json TEXT NOT NULL,
                warning_text TEXT,
                error_text TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def connect(database_path: Path) -> sqlite3.Connection:
    ensure_parent_dir(database_path)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection
