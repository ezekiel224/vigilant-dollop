"""
core/seen_db.py — persistent set of already-queued artist names.
Stored as a simple JSON file so it survives container restarts.
"""
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


class SeenDB:
    """Thread-safe (enough for our single-process use) JSON set."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._data: set[str] = set()
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                self._data = {n.lower() for n in raw}
                log.info("SeenDB: loaded %d known artists from %s", len(self._data), self._path)
            except Exception as exc:
                log.warning("SeenDB: could not read %s (%s), starting fresh", self._path, exc)
                self._data = set()

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(sorted(self._data), indent=2))

    def seen(self, name: str) -> bool:
        return name.lower() in self._data

    def mark(self, name: str):
        self._data.add(name.lower())
        self._save()

    def mark_many(self, names: list[str]):
        for n in names:
            self._data.add(n.lower())
        self._save()

    def __len__(self):
        return len(self._data)
