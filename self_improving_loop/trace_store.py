"""Trace storage primitives.

The default store stays intentionally small and stdlib-only, but it must still
be safe enough for multi-worker agent processes.  JSONL remains the portable
format; a sidecar lock file serializes append/read access across processes.
"""

from __future__ import annotations

import contextlib
import gzip
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional


@contextlib.contextmanager
def _exclusive_file_lock(lock_path: Path) -> Iterator[None]:
    """Cross-platform exclusive lock using only the Python stdlib."""

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as lock_file:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


class JsonlTraceStore:
    """Append-only JSONL trace store with process-safe writes.

    Optional size-based rotation keeps long-running deployments from growing a
    single multi-GB ``traces.jsonl`` forever.  Rotation and compaction both use
    the same sidecar lock as appends, so cron jobs can run safely next to
    worker processes.
    """

    def __init__(
        self,
        path: Path | str,
        max_bytes: Optional[int] = None,
        archive_dir: Optional[Path | str] = None,
        max_archives: int = 5,
    ):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.max_bytes = max_bytes
        self.archive_dir = Path(archive_dir) if archive_dir is not None else (
            self.path.parent / "trace_archives"
        )
        self.max_archives = max_archives

        if self.max_bytes is not None and self.max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        if self.max_archives < 1:
            raise ValueError("max_archives must be at least 1")

        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, trace: Dict) -> None:
        """Append a single trace atomically under the sidecar lock."""

        line = json.dumps(trace, ensure_ascii=False)
        with _exclusive_file_lock(self.lock_path):
            self._rotate_if_needed_unlocked()
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())

    def load(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Load valid traces, skipping corrupt lines instead of crashing."""

        if not self.path.exists():
            return []

        traces: List[Dict] = []
        with _exclusive_file_lock(self.lock_path):
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        trace = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if agent_id is None or trace.get("agent_id") == agent_id:
                        traces.append(trace)
        return traces

    def rotate(self, force: bool = False) -> Optional[Path]:
        """Rotate the current JSONL file into a gzipped archive.

        Args:
            force: rotate even when ``max_bytes`` has not been reached.

        Returns:
            The created archive path, or ``None`` when no rotation was needed.
        """

        with _exclusive_file_lock(self.lock_path):
            return self._rotate_if_needed_unlocked(force=force)

    def compact(self, max_entries: int) -> int:
        """Keep only the latest valid trace entries in the active JSONL file.

        Corrupt JSONL rows are dropped during compaction.  This is intended for
        user-controlled maintenance jobs, not automatic lossy cleanup.

        Returns:
            Number of valid trace entries removed.
        """

        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        if not self.path.exists():
            return 0

        with _exclusive_file_lock(self.lock_path):
            valid_rows = self._load_all_valid_unlocked()
            kept_rows = valid_rows[-max_entries:]
            removed = len(valid_rows) - len(kept_rows)
            temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                for row in kept_rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.path)
            return removed

    def _load_all_valid_unlocked(self) -> List[Dict]:
        rows: List[Dict] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def _rotation_archive_path_unlocked(self) -> Path:
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        base = f"{self.path.stem}-{timestamp}{self.path.suffix}.gz"
        candidate = self.archive_dir / base
        counter = 1
        while candidate.exists():
            candidate = self.archive_dir / (
                f"{self.path.stem}-{timestamp}-{counter}{self.path.suffix}.gz"
            )
            counter += 1
        return candidate

    def _rotate_if_needed_unlocked(self, force: bool = False) -> Optional[Path]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        if not force and (
            self.max_bytes is None or self.path.stat().st_size <= self.max_bytes
        ):
            return None

        archive_path = self._rotation_archive_path_unlocked()
        with open(self.path, "rb") as src, gzip.open(archive_path, "wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
        self.path.unlink()
        self._prune_archives_unlocked()
        return archive_path

    def _prune_archives_unlocked(self) -> None:
        pattern = f"{self.path.stem}-*{self.path.suffix}.gz"
        archives = sorted(
            self.archive_dir.glob(pattern),
            key=lambda p: (p.stat().st_mtime_ns, p.name),
            reverse=True,
        )
        for archive in archives[self.max_archives:]:
            archive.unlink()


class SQLiteTraceStore:
    """SQLite trace store for multi-worker production runs.

    JSONL stays the default because it is transparent and easy to inspect.
    SQLite is the safer option when several worker processes append traces over
    a long-running deployment.  It uses stdlib sqlite3 plus WAL mode; no extra
    dependency is required.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    timestamp TEXT,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_traces_agent_id ON traces(agent_id)"
            )

    def append(self, trace: Dict) -> None:
        """Append a trace under SQLite's transactional write lock."""

        payload = json.dumps(trace, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO traces(agent_id, timestamp, payload) VALUES (?, ?, ?)",
                (
                    trace.get("agent_id"),
                    trace.get("timestamp"),
                    payload,
                ),
            )

    def load(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Load traces in insertion order."""

        if not self.path.exists():
            return []

        query = "SELECT payload FROM traces"
        params: tuple = ()
        if agent_id is not None:
            query += " WHERE agent_id = ?"
            params = (agent_id,)
        query += " ORDER BY id ASC"

        traces: List[Dict] = []
        with self._connect() as conn:
            for (payload,) in conn.execute(query, params):
                try:
                    traces.append(json.loads(payload))
                except json.JSONDecodeError:
                    continue
        return traces


def append_jsonl(path: Path | str, entries: Iterable[Dict]) -> None:
    """Small helper for tests and migrations."""

    store = JsonlTraceStore(path)
    for entry in entries:
        store.append(entry)
