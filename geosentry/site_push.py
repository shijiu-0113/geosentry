"""IndexNow 推送（纯 stdlib）。

从 facts.json 读 URL 列表，POST api.indexnow.org 通知搜索引擎更新索引。
首次运行提示在站点根目录放 key.txt。
"""
from __future__ import annotations

import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Optional

INDEXNOW_URL = "https://api.indexnow.org/IndexNow"


def load_urls_from_facts(facts_path: Path) -> List[str]:
    """从 facts.json 读 URL 列表（rows[].url）。"""
    data = json.loads(facts_path.read_text(encoding="utf-8"))
    return [r["url"] for r in data.get("rows", []) if r.get("url")]


def push_indexnow(host: str, key: str, urls: List[str],
                  key_location: Optional[str] = None,
                  timeout: int = 15) -> dict:
    """POST IndexNow 请求。
    body: {host, key, keyLocation, urlList}
    返回 {ok, status, reason}。
    403/429 不误报成功。
    """
    payload = {
        "host": host,
        "key": key,
        "keyLocation": key_location or f"https://{host}/{key}.txt",
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        INDEXNOW_URL, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"ok": r.status in (200, 202), "status": r.status,
                    "reason": "accepted"}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code,
                "reason": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"ok": False, "status": None, "reason": str(e)[:120]}
