"""M2.10: URL→raw HTML 磁盘缓存。
out/.cache/<sha1(normalized_url)>.html，存 ETag/Last-Modified。
二次审计发条件请求，304 直接用旧缓存。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional, Tuple

from .site_audit import normalize_url


def _cache_key(url: str) -> str:
    """缓存 key = sha1(normalized_url)。"""
    n = normalize_url(url)
    return hashlib.sha1(n.encode("utf-8")).hexdigest()


class DiskCache:
    def __init__(self, cache_dir: Path, enabled: bool = True):
        self.dir = Path(cache_dir)
        self.enabled = enabled
        if enabled:
            self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, url: str) -> Path:
        return self.dir / (_cache_key(url) + ".html")

    def _meta_path(self, url: str) -> Path:
        return self.dir / (_cache_key(url) + ".json")

    def get(self, url: str) -> Optional[bytes]:
        """返回缓存的 HTML bytes，无则 None。"""
        if not self.enabled:
            return None
        p = self._path(url)
        if p.exists():
            return p.read_bytes()
        return None

    def get_conditional_headers(self, url: str) -> dict:
        """返回 If-None-Match / If-Modified-Since 头（有缓存时）。"""
        if not self.enabled:
            return {}
        mp = self._meta_path(url)
        if mp.exists():
            meta = json.loads(mp.read_text(encoding="utf-8"))
            h = {}
            if meta.get("etag"):
                h["If-None-Match"] = meta["etag"]
            if meta.get("last_modified"):
                h["If-Modified-Since"] = meta["last_modified"]
            return h
        return {}

    def put(self, url: str, html: bytes, etag: str = "", last_modified: str = ""):
        """存 HTML + meta。"""
        if not self.enabled:
            return
        self._path(url).write_bytes(html)
        self._meta_path(url).write_text(json.dumps({
            "url": url, "etag": etag, "last_modified": last_modified,
        }), encoding="utf-8")

    def refresh(self, url: str):
        """删除缓存条目。"""
        for ext in (".html", ".json"):
            p = self.dir / (_cache_key(url) + ext)
            if p.exists():
                p.unlink()
