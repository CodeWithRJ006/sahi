"""Content-addressed local disk cache with atomic write safety."""

import os
import json
import hashlib
import tempfile
from typing import Optional, Dict, Any

class ContentAddressedCache:
    """
    Thread-safe, process-safe local cache storing responses under `.cache/`.
    Keys are deterministic SHA-256 digests over request parameters (excluding credentials).
    """

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    @staticmethod
    def compute_key(
        provider: str,
        model: str,
        action: str,
        payload_data: Any,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Computes a deterministic SHA-256 hex digest for request components.
        Never include API keys or authentication headers in payload_data or extra_params.
        """
        hasher = hashlib.sha256()
        hasher.update(provider.strip().lower().encode("utf-8"))
        hasher.update(model.strip().lower().encode("utf-8"))
        hasher.update(action.strip().lower().encode("utf-8"))

        if isinstance(payload_data, (bytes, bytearray)):
            hasher.update(payload_data)
        elif isinstance(payload_data, str):
            hasher.update(payload_data.encode("utf-8"))
        elif isinstance(payload_data, (dict, list)):
            canonical_json = json.dumps(payload_data, sort_keys=True, separators=(",", ":"))
            hasher.update(canonical_json.encode("utf-8"))
        else:
            hasher.update(str(payload_data).encode("utf-8"))

        if extra_params:
            # Strip any credentials if accidentally provided
            filtered_params = {
                k: v for k, v in extra_params.items()
                if not any(secret in k.lower() for secret in ["key", "token", "auth", "secret", "password"])
            }
            canonical_params = json.dumps(filtered_params, sort_keys=True, separators=(",", ":"))
            hasher.update(canonical_params.encode("utf-8"))

        return hasher.hexdigest()

    def _get_path(self, cache_key: str) -> str:
        # Shard into subdirectories by first 2 chars to avoid directory file crowding
        prefix = cache_key[:2]
        shard_dir = os.path.join(self.cache_dir, prefix)
        os.makedirs(shard_dir, exist_ok=True)
        return os.path.join(shard_dir, f"{cache_key}.json")

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached JSON payload if present, else None."""
        path = self._get_path(cache_key)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Atomically saves JSON payload using a temporary file and replace.
        Prevents corrupt reads during concurrent executions.
        """
        target_path = self._get_path(cache_key)
        target_dir = os.path.dirname(target_path)

        # Write to temporary file in same filesystem directory for atomic os.replace
        temp_fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix="tmp_cache_")
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, target_path)
        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise
