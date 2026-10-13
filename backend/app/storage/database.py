"""SQLite persistence engine, connection manager, and schema definitions."""

import os
import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_FILENAME = "practice_coach.db"


def resolve_db_path() -> str:
    """Resolve the SQLite database file path from environment variables or default."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    env_path = os.getenv("PRACTICE_COACH_DB_PATH") or os.getenv("DATABASE_URL")
    if env_path:
        path_str = env_path
        if path_str.startswith("sqlite:///"):
            path_str = path_str[len("sqlite:///") :]
        elif path_str.startswith("sqlite://"):
            path_str = path_str[len("sqlite://") :]

        if path_str == ":memory:" or path_str.startswith("file:mem"):
            return path_str
        if not os.path.isabs(path_str):
            return str((base_dir / path_str).resolve())
        return path_str

    # Default location: backend directory root
    return str((base_dir / DEFAULT_DB_FILENAME).resolve())


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    language TEXT NOT NULL DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS audio_metrics (
    session_id TEXT PRIMARY KEY,
    has_metrics INTEGER NOT NULL DEFAULT 1,
    transcript TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT 'en',
    language_probability REAL NOT NULL DEFAULT 1.0,
    total_duration_seconds REAL NOT NULL DEFAULT 0.0,
    speaking_duration_seconds REAL NOT NULL DEFAULT 0.0,
    total_words INTEGER NOT NULL DEFAULT 0,
    words_per_minute REAL NOT NULL DEFAULT 0.0,
    articulation_rate_wpm REAL NOT NULL DEFAULT 0.0,
    filler_words_count INTEGER NOT NULL DEFAULT 0,
    filler_words_ratio REAL NOT NULL DEFAULT 0.0,
    filler_words_breakdown_json TEXT NOT NULL DEFAULT '{}',
    pause_count INTEGER NOT NULL DEFAULT 0,
    total_pause_duration_seconds REAL NOT NULL DEFAULT 0.0,
    average_pause_duration_seconds REAL NOT NULL DEFAULT 0.0,
    longest_pause_duration_seconds REAL NOT NULL DEFAULT 0.0,
    pause_threshold_seconds REAL NOT NULL DEFAULT 0.5,
    pauses_json TEXT NOT NULL DEFAULT '[]',
    segments_json TEXT NOT NULL DEFAULT '[]',
    words_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS visual_metrics (
    session_id TEXT PRIMARY KEY,
    total_duration_seconds REAL NOT NULL DEFAULT 0.0,
    frames_analyzed INTEGER NOT NULL DEFAULT 0,
    face_detected_ratio REAL NOT NULL DEFAULT 0.0,
    centered_gaze_ratio REAL NOT NULL DEFAULT 0.0,
    gaze_distribution_json TEXT NOT NULL DEFAULT '{}',
    head_stability_score REAL NOT NULL DEFAULT 0.0,
    head_movement_variance REAL NOT NULL DEFAULT 0.0,
    hands_visible_ratio REAL NOT NULL DEFAULT 0.0,
    hand_gestures_per_minute REAL NOT NULL DEFAULT 0.0,
    tracking_notes_json TEXT NOT NULL DEFAULT '[]',
    ethical_disclaimer TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_feature_vectors (
    session_id TEXT PRIMARY KEY,
    session_index INTEGER NOT NULL DEFAULT 0,
    timestamp_iso TEXT,
    has_audio INTEGER NOT NULL DEFAULT 0,
    has_visual INTEGER NOT NULL DEFAULT 0,
    words_per_minute REAL NOT NULL DEFAULT 0.0,
    articulation_rate_wpm REAL NOT NULL DEFAULT 0.0,
    filler_words_ratio REAL NOT NULL DEFAULT 0.0,
    average_pause_duration_seconds REAL NOT NULL DEFAULT 0.0,
    pause_frequency_per_minute REAL NOT NULL DEFAULT 0.0,
    centered_gaze_ratio REAL NOT NULL DEFAULT 0.0,
    head_stability_score REAL NOT NULL DEFAULT 0.0,
    hand_gestures_per_minute REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
"""


class Database:
    """Manages SQLite database connections, initialization, and transaction lifecycles."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or resolve_db_path()
        self._is_memory = self.db_path == ":memory:" or self.db_path.startswith("file:mem")
        self._memory_conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

        if not self._is_memory:
            # Ensure target parent directory exists
            db_dir = os.path.dirname(os.path.abspath(self.db_path))
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        else:
            # Persistent in-memory connection
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")

        self._init_db()

    def _init_db(self) -> None:
        """Create database tables and apply default pragmas."""
        with self.connection() as conn:
            if not self._is_memory:
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                except sqlite3.Error:
                    pass
            conn.executescript(SCHEMA_SQL)

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an active SQLite connection with automatic commit/rollback."""
        if self._is_memory and self._memory_conn is not None:
            with self._lock:
                try:
                    yield self._memory_conn
                    self._memory_conn.commit()
                except Exception:
                    self._memory_conn.rollback()
                    raise
            return

        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        """Close persistent connections if open."""
        if self._memory_conn is not None:
            try:
                self._memory_conn.close()
            except sqlite3.Error:
                pass
            self._memory_conn = None


_db_instance: Database | None = None
_db_lock = threading.Lock()


def get_database(db_path: str | None = None) -> Database:
    """Thread-safe accessor for the default Database instance."""
    global _db_instance
    with _db_lock:
        if _db_instance is None or (db_path and _db_instance.db_path != db_path):
            _db_instance = Database(db_path=db_path)
        return _db_instance


def reset_database() -> None:
    """Reset the global database instance (useful between test suites)."""
    global _db_instance
    with _db_lock:
        if _db_instance is not None:
            _db_instance.close()
            _db_instance = None
