"""Trace storage primitives.

The default store stays intentionally small and stdlib-only, but it must still
be safe enough for multi-worker agent processes.  JSONL remains the portable
format; a sidecar lock file serializes append/read access across processes.
"""

from __future__ import annotations

import contextlib
import json
import os
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
    """Append-only JSONL trace store with process-safe writes."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, trace: Dict) -> None:
        """Append a single trace atomically under the sidecar lock."""

        line = json.dumps(trace, ensure_ascii=False)
        with _exclusive_file_lock(self.lock_path):
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


def append_jsonl(path: Path | str, entries: Iterable[Dict]) -> None:
    """Small helper for tests and migrations."""

    store = JsonlTraceStore(path)
    for entry in entries:
        store.append(entry)
