"""可选增强：PageSpeed/Lighthouse API + Email/DNS 检查。

纯标准库 HTTP 调用 PageSpeed Insights API；DNS 检查依赖可选 dnspython。
无 API key 或无 dnspython 时优雅跳过，返回 skipped=True。
结果单独成节、不计入主分。
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional


def run_pagespeed(url: str, api_key: str = "", strategy: str = "mobile",
                  timeout: int = 6) -> dict:
    """调 Google PageSpeed Insights API。
    无 api_key 时仍可调用（限流），返回 {skipped, performance, accessibility,
    best_practices, seo, lcp, cls, fcp, ttfb, error}。
    """
    api_url = ("https://www.googleapis.com/pagespeedonline/v5/runPagespeed?"
               f"url={urllib.parse.quote(url)}&strategy={strategy}")
    if api_key:
        api_url += f"&key={api_key}"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "geosentry/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        lh = data.get("lighthouseResult", {})
        cats = lh.get("categories", {})
        audits = lh.get("audits", {})
        def _score(name):
            v = cats.get(name, {}).get("score")
            return round(v * 100) if v is not None else None
        def _metric(aid):
            v = audits.get(aid, {}).get("numericValue")
            return round(v, 0) if v is not None else None
        return {
            "skipped": False,
            "performance": _score("performance"),
            "accessibility": _score("accessibility"),
            "best_practices": _score("best-practices"),
            "seo": _score("seo"),
            "lcp_ms": _metric("largest-contentful-paint"),
            "cls": _metric("cumulative-layout-shift"),
            "fcp_ms": _metric("first-contentful-paint"),
            "ttfb_ms": _metric("server-response-time"),
            "inp_ms": _metric("interaction-to-next-paint"),
        }
    except Exception as e:
        return {"skipped": True, "error": str(e)[:120]}


def run_dns_email_checks(domain: str) -> dict:
    """查 SPF/DKIM/DMARC/MTA-STS TXT 记录。
    依赖可选 dnspython；未安装时返回 skipped=True。
    """
    try:
        import dns.resolver  # type: ignore
    except ImportError:
        return {"skipped": True,
                "note": "dnspython 未安装；pip install dnspython 后启用",
                "records": {}}

    resolver = dns.resolver.Resolver()
    resolver.timeout = 8
    resolver.lifetime = 8
    out = {}
    # SPF: 根域 TXT
    try:
        ans = resolver.resolve(domain, "TXT")
        spf = [r.to_text() for r in ans if "v=spf1" in r.to_text().lower()]
        out["spf"] = spf[0] if spf else None
    except Exception as e:
        out["spf"] = f"error: {e}"
    # DMARC: _dmarc.domain TXT
    try:
        ans = resolver.resolve(f"_dmarc.{domain}", "TXT")
        out["dmarc"] = ans[0].to_text() if ans else None
    except Exception as e:
        out["dmarc"] = f"error: {e}"
    # MTA-STS: _mta-sts.domain TXT
    try:
        ans = resolver.resolve(f"_mta-sts.{domain}", "TXT")
        out["mta_sts"] = ans[0].to_text() if ans else None
    except Exception as e:
        out["mta_sts"] = f"error: {e}"
    return {"skipped": False, "records": out}


def run_bing_webmaster(site_url: str, api_key: str = "") -> dict:
    """M2.6: Bing Webmaster Tools 外链清单（只读骨架）。
    无 key → skipped=True；有 key 时调 Bing WMT API。
    """
    if not api_key:
        return {"skipped": True, "note": "未提供 --bing-webmaster-key"}
    # Bing WMT API: https://www.bing.com/webmaster/api
    try:
        import urllib.request, json
        url = f"https://www.bing.com/webmaster/api.svc/json/GetLinkCounts?siteUrl={site_url}"
        req = urllib.request.Request(url, headers={"ApiKey": api_key})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {"skipped": False, "data": data}
    except Exception as e:
        return {"skipped": True, "error": str(e)[:120]}


def check_dkim(domain: str, selectors: list = None) -> dict:
    """M2.7: DKIM 检查（查 selector._domainkey.domain TXT）。
    依赖 dnspython；未安装时 skipped=True。
    """
    selectors = selectors or ["default", "selector1", "selector2", "google", "k1"]
    try:
        import dns.resolver  # type: ignore
    except ImportError:
        return {"skipped": True, "note": "dnspython 未安装", "records": {}}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 5
    out = {}
    for sel in selectors:
        name = f"{sel}._domainkey.{domain}"
        try:
            ans = resolver.resolve(name, "TXT")
            out[sel] = ans[0].to_text()[:80] if ans else None
        except Exception:
            out[sel] = None
    found = any(v for v in out.values())
    return {"skipped": False, "found": found, "records": out}


def gsc_verification_guide(domain: str) -> dict:
    """M3.2: GSC/Bing 所有权验证指引（三选一）。"""
    return {
        "skipped": False,
        "guide": {
            "dns_txt": f"在 DNS 添加 TXT 记录: google-site-verification=... (Google Search Console)",
            "html_file": f"在 https://{domain}/ 上传 Google 提供的 .html 验证文件",
            "meta_tag": f"在首页 <head> 加 <meta name='google-site-verification' content='...'>",
            "bing": f"在 Bing Webmaster Tools 用同一 GSC 账号关联，无需重复验证",
        },
    }


def run_lighthouse_cli(url: str) -> dict:
    """M3.3: 可选 Lighthouse CLI 渲染旁路（subprocess，不引入 Python 依赖）。
    需本机安装 lighthouse CLI；未安装时 skipped=True。
    """
    import subprocess, shutil, json, tempfile
    if not shutil.which("lighthouse"):
        return {"skipped": True, "note": "lighthouse CLI 未安装；npm install -g lighthouse"}
    try:
        with tempfile.TemporaryDirectory() as td:
            out = subprocess.run(
                ["lighthouse", url, "--output=json", f"--output-path={td}/r.json",
                 "--chrome-flags=--headless", "--quiet"],
                capture_output=True, timeout=120, text=True)
            if out.returncode != 0:
                return {"skipped": True, "error": out.stderr[:120]}
            import json
            data = json.load(open(f"{td}/r.json", encoding="utf-8"))
            cats = data.get("categories", {})
            return {"skipped": False,
                    "performance": round(cats.get("performance", {}).get("score", 0) * 100),
                    "seo": round(cats.get("seo", {}).get("score", 0) * 100),
                    "best_practices": round(cats.get("best-practices", {}).get("score", 0) * 100)}
    except Exception as e:
        return {"skipped": True, "error": str(e)[:120]}
