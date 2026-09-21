"""加权总分（A-F 等级）。

汇总安全头 / sitemap 质量 / 图片优化 / 404 处理 四大类检查，
按权重加权出百分制总分，映射 A-F 等级。
权重：severe=10, medium=5, low=2。
"""
from __future__ import annotations

from typing import Dict, List, Optional

SEVERITY_WEIGHTS = {"severe": 10, "medium": 5, "low": 2}


def _grade(pct: float) -> str:
    if pct >= 90: return "A"
    if pct >= 75: return "B"
    if pct >= 60: return "C"
    if pct >= 40: return "D"
    return "F"


def compute_overall_score(security_results: Optional[List[dict]] = None,
                         sitemap_checks: Optional[List[dict]] = None,
                         image_checks: Optional[List[dict]] = None,
                         not_found_result: Optional[dict] = None,
                         psi_result: Optional[dict] = None) -> dict:
    """汇总所有可量化检查项，返回 {earned, total, pct, grade, breakdown}。

    每类检查贡献若干 (severity, passed) 项；权重按 severity 取值。
    离线模式下未采集的类传 None，不计入分母。
    """
    earned = total = 0
    breakdown = []

    def add(items: List[dict], category: str):
        nonlocal earned, total
        cat_earned = cat_total = 0
        for it in items:
            w = SEVERITY_WEIGHTS.get(it.get("severity", "low"), 2)
            cat_total += w
            if it.get("passed"):
                cat_earned += w
        earned += cat_earned
        total += cat_total
        breakdown.append({"category": category,
                          "earned": cat_earned, "total": cat_total,
                          "pct": round(cat_earned / cat_total * 100, 1) if cat_total else 0})

    # A. 安全头（每项自带 severity）
    if security_results is not None:
        add(security_results, "安全响应头")
    else:
        breakdown.append({"category": "安全响应头", "earned": 0, "total": 0,
                          "pct": None, "note": "离线未采集"})

    # F. sitemap 质量（medium: xml_valid, has_urls, has_lastmod, robots_sm; low: no_privacy_leak）
    if sitemap_checks is not None:
        sm_items = []
        for c in sitemap_checks:
            sev = "medium" if c["key"] in ("xml_valid", "has_url_entries",
                                            "has_lastmod", "robots_declares_sitemap") else "low"
            sm_items.append({"passed": c["passed"], "severity": sev})
        add(sm_items, "sitemap 质量")
    else:
        breakdown.append({"category": "sitemap 质量", "earned": 0, "total": 0,
                          "pct": None, "note": "离线未采集"})

    # G. 图片优化（medium: dimensions, alt; low: modern_format, lazy, fetchpriority）
    if image_checks is not None:
        img_items = []
        for c in image_checks:
            sev = "medium" if c["key"] in ("img_dimensions", "img_alt") else "low"
            img_items.append({"passed": c["passed"], "severity": sev})
        add(img_items, "图片优化")
    else:
        breakdown.append({"category": "图片优化", "earned": 0, "total": 0,
                          "pct": None, "note": "离线未采集"})

    # D. 404 处理（medium: soft_404, custom_404_ok, has_home_link）
    if not_found_result is not None:
        nf_items = [
            {"passed": not not_found_result.get("soft_404", True), "severity": "medium"},
            {"passed": not_found_result.get("custom_404_ok", False), "severity": "medium"},
        ]
        add(nf_items, "404 处理")
    else:
        breakdown.append({"category": "404 处理", "earned": 0, "total": 0,
                          "pct": None, "note": "离线未采集"})

    # M1.4: PSI Performance（medium，权重 5）— performance >= 90 为 pass
    if psi_result and not psi_result.get("skipped"):
        perf = psi_result.get("performance")
        psi_items = [{"passed": perf is not None and perf >= 90, "severity": "medium"}]
        add(psi_items, "PSI 性能")
    else:
        breakdown.append({"category": "PSI 性能", "earned": 0, "total": 0,
                          "pct": None, "note": "未采集"})

    pct = round(earned / total * 100, 1) if total else 0
    return {"earned": earned, "total": total, "pct": pct,
            "grade": _grade(pct), "breakdown": breakdown}
