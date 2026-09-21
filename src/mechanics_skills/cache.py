"""
Response and query caching utilities for academic API requests.
"""

import hashlib
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from mechanics_skills.serialization import read_json_file, write_json_file


class ResponseCache:
    """In-memory or filesystem-backed response cache with TTL."""

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None, default_ttl_s: float = 86400.0):
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.default_ttl = default_ttl_s
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache if not expired."""
        now = time.time()
        # Check in-memory
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if now < entry["expires_at"]:
                return entry["data"]
            else:
                del self._memory_cache[key]

        # Check disk
        if self.cache_dir:
            hashed = self._hash_key(key)
            fpath = self.cache_dir / f"{hashed}.json"
            if fpath.exists():
                try:
                    entry = read_json_file(fpath)
                    if now < entry.get("expires_at", 0):
                        # Populate in-memory
                        self._memory_cache[key] = entry
                        return entry.get("data")
                    else:
                        fpath.unlink(missing_ok=True)
                except Exception:
                    pass

        return None

    def set(self, key: str, data: Any, ttl_s: Optional[float] = None) -> None:
        """Store item in cache with expiration."""
        ttl = ttl_s if ttl_s is not None else self.default_ttl
        now = time.time()
        entry = {
            "key": key,
            "data": data,
            "stored_at": now,
            "expires_at": now + ttl,
        }
        self._memory_cache[key] = entry

        if self.cache_dir:
            hashed = self._hash_key(key)
            fpath = self.cache_dir / f"{hashed}.json"
            try:
                write_json_file(fpath, entry)
            except Exception:
                pass

    def clear(self) -> None:
        """Clear memory and disk cache."""
        self._memory_cache.clear()
        if self.cache_dir and self.cache_dir.exists():
            for f in self.cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
