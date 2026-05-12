"""Base collector with shared HTTP and caching logic."""
from __future__ import annotations

import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from ..models import OutbreakReport, SourceType


class BaseCollector:
    SOURCE: SourceType = SourceType.WHO_DON
    DEFAULT_TIMEOUT = 30
    USER_AGENT = "GlobalEpidemicTracker/1.0 (https://github.com/MRLMRML/global-epidemic-tracker)"

    def __init__(self, cache_dir: str = "data/cache", cache_ttl_hours: int = 6):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.USER_AGENT})

    def _cache_key(self, url: str, params: dict | None = None) -> str:
        raw = url + json.dumps(params or {}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _get_cached(self, key: str) -> Any | None:
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text())
            cached_at = datetime.fromisoformat(data["_cached_at"])
            if datetime.utcnow() - cached_at > self.cache_ttl:
                return None
            return data["payload"]
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def _set_cache(self, key: str, payload: Any) -> None:
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({
            "_cached_at": datetime.utcnow().isoformat(),
            "payload": payload,
        }, default=str))

    def fetch_json(self, url: str, params: dict | None = None, use_cache: bool = True) -> Any:
        key = self._cache_key(url, params)
        if use_cache:
            cached = self._get_cached(key)
            if cached is not None:
                return cached
        resp = self._session.get(url, params=params, timeout=self.DEFAULT_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        self._set_cache(key, payload)
        return payload

    def fetch_text(self, url: str, params: dict | None = None, use_cache: bool = True) -> str:
        key = self._cache_key(url, params)
        if use_cache:
            cached = self._get_cached(key)
            if cached is not None:
                return cached
        resp = self._session.get(url, params=params, timeout=self.DEFAULT_TIMEOUT)
        resp.raise_for_status()
        text = resp.text
        self._set_cache(key, text)
        return text

    def collect(self) -> list[OutbreakReport]:
        raise NotImplementedError
