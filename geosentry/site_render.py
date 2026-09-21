"""M3.6: 可选渲染层 — Crawl4AI / Playwright 旁路。
import 失败自动降级纯静态；与 M3.3 Lighthouse CLI 并存。
"""
from __future__ import annotations

from typing import Optional


def render_page(url: str, mode: str = "off") -> dict:
    """渲染页面返回 HTML。
    mode: off = 不渲染（返回原始请求由调用方处理）；
          crawl4ai = 尝试用 crawl4ai 渲染。
    返回 {"html": str, "rendered": bool, "skipped": bool, "note": str}
    """
    if mode == "off" or not mode:
        return {"html": "", "rendered": False, "skipped": True,
                "note": "render off"}
    if mode == "crawl4ai":
        try:
            from crawl4ai import WebCrawler  # type: ignore
            # 实际调用留 TODO（需真实 crawl4ai 实例）
            return {"html": "", "rendered": False, "skipped": True,
                    "note": "crawl4ai stub — 实际渲染待集成"}
        except ImportError:
            return {"html": "", "rendered": False, "skipped": True,
                    "note": "crawl4ai 未安装；pip install crawl4ai"}
    return {"html": "", "rendered": False, "skipped": True, "note": f"unknown mode: {mode}"}
