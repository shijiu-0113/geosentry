"""安全响应头分析（纯标准库，零依赖）。

对首页（或采样页）的 HTTP 响应头逐项检查，返回结构化结果。
每项标注 severity，按 A-F 百分制加权。
离线模式下无 headers 输入，返回全部 not_run。
"""
from __future__ import annotations

from typing import Dict, List, Optional

# 检查项定义：(key, 展示名, severity, 检查函数描述)
# severity: severe / medium / low
SECURITY_CHECKS = [
    ("hsts",            "Strict-Transport-Security (HSTS)",     "severe"),
    ("csp",             "Content-Security-Policy (CSP)",        "severe"),
    ("frame",           "X-Frame-Options 或 CSP frame-ancestors", "medium"),
    ("nosniff",         "X-Content-Type-Options: nosniff",      "medium"),
    ("referrer",        "Referrer-Policy",                      "low"),
    ("permissions",     "Permissions-Policy",                   "low"),
    ("coop",            "Cross-Origin-Opener-Policy",           "low"),
    ("coep",            "Cross-Origin-Embedder-Policy",         "low"),
    ("corp",            "Cross-Origin-Resource-Policy",         "low"),
]


def _header_lower(headers: Dict[str, str], name: str) -> str:
    """大小写不敏感地取响应头。"""
    target = name.lower()
    for k, v in headers.items():
        if k.lower() == target:
            return v or ""
    return ""


def analyze_security_headers(headers: Dict[str, str]) -> List[dict]:
    """分析 HTTP 响应头，返回每项检查结果列表。

    每项 dict: {key, name, severity, passed, detail}
    passed=True 表示通过（有该头且值合理）；False 表示缺失或值不当。
    """
    results = []
    hsts = _header_lower(headers, "Strict-Transport-Security")
    csp = _header_lower(headers, "Content-Security-Policy")
    xfo = _header_lower(headers, "X-Frame-Options")
    nosniff = _header_lower(headers, "X-Content-Type-Options")
    referrer = _header_lower(headers, "Referrer-Policy")
    permissions = _header_lower(headers, "Permissions-Policy")
    coop = _header_lower(headers, "Cross-Origin-Opener-Policy")
    coep = _header_lower(headers, "Cross-Origin-Embedder-Policy")
    corp = _header_lower(headers, "Cross-Origin-Resource-Policy")

    # HSTS: 必须存在且 max-age >= 31536000 (1年)
    if hsts:
        ok = "max-age" in hsts.lower()
        import re as _re
        m = _re.search(r"max-age=(\d+)", hsts, _re.I)
        if m:
            ok = int(m.group(1)) >= 31536000
        results.append({"key": "hsts", "name": "Strict-Transport-Security (HSTS)",
                        "severity": "severe", "passed": bool(ok),
                        "detail": hsts[:120] if ok else "缺少或 max-age < 31536000"})
    else:
        results.append({"key": "hsts", "name": "Strict-Transport-Security (HSTS)",
                        "severity": "severe", "passed": False,
                        "detail": "未设置 HSTS 响应头"})

    # CSP: 必须存在且非空
    if csp:
        results.append({"key": "csp", "name": "Content-Security-Policy (CSP)",
                        "severity": "severe", "passed": True,
                        "detail": csp[:120]})
    else:
        results.append({"key": "csp", "name": "Content-Security-Policy (CSP)",
                        "severity": "severe", "passed": False,
                        "detail": "未设置 CSP 响应头"})

    # X-Frame-Options 或 CSP frame-ancestors
    has_frame = bool(xfo) or ("frame-ancestors" in csp.lower())
    results.append({"key": "frame", "name": "X-Frame-Options 或 CSP frame-ancestors",
                    "severity": "medium", "passed": has_frame,
                    "detail": xfo if xfo else ("CSP frame-ancestors" if "frame-ancestors" in csp.lower() else "两者均未设置")})

    # nosniff
    results.append({"key": "nosniff", "name": "X-Content-Type-Options: nosniff",
                    "severity": "medium", "passed": nosniff.strip().lower() == "nosniff",
                    "detail": nosniff or "未设置"})

    # Low severity headers
    for key, name, val in [
        ("referrer", "Referrer-Policy", referrer),
        ("permissions", "Permissions-Policy", permissions),
        ("coop", "Cross-Origin-Opener-Policy", coop),
        ("coep", "Cross-Origin-Embedder-Policy", coep),
        ("corp", "Cross-Origin-Resource-Policy", corp),
    ]:
        results.append({"key": key, "name": name,
                        "severity": "low", "passed": bool(val),
                        "detail": val[:120] if val else "未设置"})
    return results


# 权重表：severe/medium/low 三级加权
SEVERITY_WEIGHTS = {"severe": 10, "medium": 5, "low": 2}


def score_security_headers(results: List[dict]) -> dict:
    """对安全头结果做加权评分，返回 {earned, total, pct, grade}。"""
    earned = total = 0
    for r in results:
        w = SEVERITY_WEIGHTS.get(r["severity"], 0)
        total += w
        if r["passed"]:
            earned += w
    pct = (earned / total * 100) if total else 0
    return {"earned": earned, "total": total, "pct": round(pct, 1),
            "passed_count": sum(1 for r in results if r["passed"]),
            "total_count": len(results)}
