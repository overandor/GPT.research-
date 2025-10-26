import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config.settings import settings


class MerkleLogger:
    """Persist round outputs with Merkle root tracking."""

    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._current_root = ""

    def log_round(self, context: Any, results: List[Dict[str, Any]]) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "context": getattr(context, "__dict__", context),
            "results": results,
        }
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(blob).hexdigest()
        self._current_root = self._combine_hash(self._current_root, digest)
        self._write_file(digest, blob)
        return self._current_root

    def _combine_hash(self, left: str, right: str) -> str:
        material = (left + right).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def _write_file(self, digest: str, blob: bytes) -> None:
        path = self.base_path / f"{digest}.json"
        path.write_bytes(blob)
        self._prune_archives()

    def _prune_archives(self) -> None:
        files = sorted(self.base_path.glob("*.json"), key=os.path.getmtime)
        excess = len(files) - settings.archive_cap
        for file in files[: max(excess, 0)]:
            file.unlink(missing_ok=True)

    def get_current_root(self) -> str:
        return self._current_root
