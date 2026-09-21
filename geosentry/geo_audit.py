"""轻量站点 GEO/SEO 审计（零第三方依赖）。

对目标站点做基础合规检查，逐项用本地知识背板检索 Google 官方依据，
输出「现状 → 官方要求 → 出处」报告。完整 geo-optimizer-skill 深度审计
留作可选增强（见 README）。

检查项：robots.txt / AI 爬虫放行 / title / meta description / H1 /
页面字数（中英文通算）/ JSON-LD schema / llms.txt / canonical /
OG 标签 / sitemap.xml / viewport / charset / HTTPS。
"""
from __future__ import annotations

import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

socket.setdefaulttimeout(15)
UA = "geosentry-audit/0.1 (research; contact: dev@example.com)"

CHECKS = [
    ("robots", "robots.txt 存在且未全站 Disallow 抓取"),
    ("title", "页面存在 title 标签"),
    ("meta", "页面存在 meta description"),
    ("h1", "页面存在 H1 标题"),
    ("content", "正文内容足够（>=300 词，中英文通算）"),
    ("schema", "页面存在 JSON-LD / 结构化数据"),
    ("llms", "站点根目录存在 llms.txt（GEO 生态实践）"),
    ("canonical", "页面声明 canonical URL"),
    ("og", "页面存在 Open Graph 标签"),
    ("sitemap", "站点声明 sitemap.xml（在 robots.txt 或可访问）"),
    ("viewport", "页面声明 viewport（移动端友好基础）"),
    ("charset", "页面声明字符编码"),
    ("https", "站点通过 HTTPS 提供服务"),
]


def _build_ssl_context(verify: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_get(url: str, timeout: int = 15, verify: bool = True) -> Optional[tuple]:
    """返回 (status_code, text) 或 None；SSL 默认校验。"""
    ctx = _build_ssl_context(verify)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        # 4xx/5xx 也算响应存在；robots.txt 404 视为不存在
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, body
    except Exception:
        return None


def _norm(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _extract_title(html: str) -> Optional[str]:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip() if m else None


def _count_words(html: str) -> int:
    """中英文通算：英文按单词，中文按字符（一个汉字算 1 词）。"""
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    body = re.sub(r"<[^>]+>", " ", body)
    en = len(re.findall(r"[A-Za-z]{2,}", body))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", body))
    return en + cjk


def _robots_allows_home(robots_txt: str, target_path: str = "/") -> bool:
    """简化 robots.txt 解析：User-agent: * 段下，检查 Disallow 是否覆盖目标路径。
    未声明 robots.txt 或无 Disallow 规则视为允许。"""
    if not robots_txt:
        return True
    in_wild = False
    disallows = []
    for raw in robots_txt.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(?i)^user-agent:\s*(.+)$", line)
        if m:
            ua_val = m.group(1).strip()
            in_wild = ua_val == "*"
            continue
        if in_wild:
            md = re.match(r"(?i)^disallow:\s*(.*)$", line)
            if md:
                path = md.group(1).strip()
                disallows.append(path)
    for d in disallows:
        if d in ("", "/"):
            # Disallow: 或 Disallow: / 等于全站禁止
            return False
        if d and d != "/" and target_path.startswith(d):
            return False
    return True


def _robots_refer_sitemap(robots_txt: str) -> bool:
    if not robots_txt:
        return False
    return bool(re.search(r"(?i)^sitemap:\s*\S+", robots_txt, re.M))


# GEO 场景重点关注的 AI 爬虫 UA
_AI_BOTS = ("GPTBot", "OAI-SearchBot", "ChatGPT-User",
            "ClaudeBot", "Claude-Web", "Claude-User", "Claude-SearchBot",
            "PerplexityBot", "Google-Extended")


def _parse_robots_bots(robots_txt: str) -> dict:
    """把 robots.txt 按行解析成 {ua_lower: [(path, allow_bool), ...]}。
    未声明某 bot 时默认允许。"""
    rules: dict = {}
    current_ua: Optional[str] = None
    for raw in robots_txt.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(?i)^user-agent:\s*(.+)$", line)
        if m:
            current_ua = m.group(1).strip().lower()
            rules.setdefault(current_ua, [])
            continue
        if current_ua is None:
            continue
        md = re.match(r"(?i)^(disallow|allow):\s*(.*)$", line)
        if md:
            action = md.group(1).lower() == "allow"
            path = md.group(2).strip()
            rules[current_ua].append((path, action))
    return rules


def _bot_allowed_root(rules: dict, bot: str) -> bool:
    """判断某 bot 是否被允许抓取 / 路径。
    优先 bot 专属段，无则回退 * 段；段内存在 Disallow: 或 Disallow: / 即视为禁止。
    未声明该 bot 也无 * 段时默认允许。"""
    bot_l = bot.lower()
    section = rules.get(bot_l) or rules.get("*") or []
    for path, allow in section:
        if not allow and path in ("", "/"):
            return False
    return True


def _validate_llmstxt(text: str) -> list[str]:
    """校验 llms.txt 结构：首行 # 标题、> blockquote 摘要、- [title](绝对URL) 列表、URL 不重复。
    返回错误列表（空列表 = 通过）。"""
    errors = []
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ["文件为空"]
    if not lines[0].startswith("# "):
        errors.append("首行必须是 '# 项目标题'")
    # 找 blockquote（> 开头）
    has_blockquote = any(l.startswith("> ") for l in lines)
    if not has_blockquote:
        errors.append("缺少 '> 一句话摘要' blockquote 段")
    # 列表项：- [title](URL)
    link_re = re.compile(r"^\s*-\s+\[([^\]]+)\]\((https?://[^)]+)\)")
    urls = []
    list_lines = [l for l in lines if l.lstrip().startswith("- ")]
    if not list_lines:
        errors.append("缺少 '- [title](URL)' 链接列表")
    else:
        for l in list_lines:
            m = link_re.match(l)
            if not m:
                errors.append(f"列表项格式不符（应为 - [title](https://...)）: {l[:60]}")
            else:
                urls.append(m.group(2))
    # URL 重复
    seen = set()
    for u in urls:
        if u in seen:
            errors.append(f"URL 重复: {u}")
        seen.add(u)

    # C: llms.txt 质量加查
    head = text[:500]
    # 纯文本非 HTML/JSON
    if "<html" in head.lower() or "<!doctype" in head.lower():
        errors.append("llms.txt 首 500 字符含 HTML 标签（应为纯文本 Markdown）")
    if head.lstrip().startswith("{") or head.lstrip().startswith("["):
        errors.append("llms.txt 首字符为 JSON（应为纯文本 Markdown）")
    # 文件大小 < 100KB
    if len(text.encode("utf-8")) > 100 * 1024:
        errors.append("llms.txt 超过 100KB（应精简为索引清单）")
    # 至少列一个团队成员或内容 URL（已有 urls 列表即满足）
    if not urls:
        errors.append("llms.txt 未列出任何团队成员或内容 URL")
    # 首 500 字符应含公司名/描述（启发式：有 # 标题 + > 摘要即可，宽松判定）
    if not any(l.startswith("#") for l in lines[:3]):
        errors.append("llms.txt 首段未见 # 标题，疑似缺少公司名/项目名")
    return errors


def run_audit(url: str, top_k: int = 3, verify_ssl: bool = True) -> int:
    from . import GeoSentry

    base = _norm(url)
    if not base:
        print("URL 不能为空。")
        return 2
    bp = GeoSentry()
    if not bp.info()["indexed"]:
        print("尚未建立索引，请先运行: python -m geosentry index")
        return 1

    print(f"# GEO/SEO 基础审计: {base}")
    print(f"- 时间: {datetime.now().isoformat(timespec='seconds')}\n")

    home_resp = _http_get(base + "/", verify=verify_ssl)
    robots_resp = _http_get(base + "/robots.txt", verify=verify_ssl)
    llms_resp = _http_get(base + "/llms.txt", verify=verify_ssl)

    html = home_resp[1] if home_resp else ""
    robots_txt = robots_resp[1] if (robots_resp and robots_resp[0] == 200) else ""

    checks = {}
    # robots：文件存在且未全站 Disallow
    checks["robots"] = bool(robots_resp and robots_resp[0] == 200
                            and _robots_allows_home(robots_txt, "/"))
    checks["title"] = bool(html and _extract_title(html))
    checks["meta"] = bool(html and re.search(r'<meta[^>]+name=["\']description["\']', html, re.I))
    checks["h1"] = bool(html and re.search(r"<h1[^>]*>", html, re.I))
    checks["content"] = bool(html and _count_words(html) >= 300)
    checks["schema"] = bool(html and re.search(r'<script[^>]+type=["\']application/ld\+json["\']', html, re.I))
    checks["llms"] = bool(llms_resp and llms_resp[0] == 200)
    checks["canonical"] = bool(html and re.search(r'<link[^>]+rel=["\']canonical["\']', html, re.I))
    checks["og"] = bool(html and re.search(r'<meta[^>]+property=["\']og:', html, re.I))
    checks["sitemap"] = _robots_refer_sitemap(robots_txt)
    checks["viewport"] = bool(html and re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I))
    checks["charset"] = bool(html and re.search(r'<meta[^>]+charset\s*=', html, re.I)
                              or re.search(r"<meta[^>]+http-equiv=[\"']Content-Type[\"']", html, re.I))
    checks["https"] = base.startswith("https://")

    passed = sum(1 for v in checks.values() if v)
    score = round(passed / len(checks) * 100)
    band = "good" if score >= 80 else ("warn" if score >= 50 else "critical")
    print(f"- 得分: {score}/100（{band}）· 通过 {passed}/{len(checks)} 项\n")

    queries = {
        "robots": "How should robots.txt control Googlebot and AI crawler access with allow and disallow rules?",
        "title": "How do title tags appear in Google search results and best practices?",
        "meta": "How do meta descriptions appear in search snippets?",
        "h1": "What heading structure does Google recommend for content?",
        "content": "What does Google define as helpful people-first content and page quality?",
        "schema": "What structured data JSON-LD types does Google require for rich results?",
        "llms": "Does Google Search use llms.txt files for ranking?",
        "canonical": "How should canonical and duplicate URLs be consolidated?",
        "og": "How do social media and preview tags affect search results?",
        "sitemap": "How should sitemap files help search engines discover pages?",
        "viewport": "What mobile-friendly viewport and rendering guidelines does Google recommend?",
        "charset": "What HTML character encoding and language declarations does Google recommend?",
        "https": "Why does Google recommend HTTPS for secure websites?",
    }

    for name, label in CHECKS:
        status = "✅" if checks[name] else "❌"
        print(f"{status} {label}")
        if not checks[name]:
            q = queries[name]
            hits = bp.search(q, top_k=top_k)
            if hits:
                h = hits[0]
                print(f"   → 官方要求（{h['doc']}）: {h['text'][:120].strip()}")
                if h.get("url"):
                    print(f"     出处: {h['url']}")

    # AI 爬虫放行明细（robots.txt 逐 bot 解析）
    if robots_txt:
        bot_rules = _parse_robots_bots(robots_txt)
        print("\nAI 爬虫放行明细（robots.txt 对 / 路径）:")
        for bot in _AI_BOTS:
            allowed = _bot_allowed_root(bot_rules, bot)
            tag = "允许" if allowed else "禁止"
            print(f"   {bot:20s}: {tag}")

    # llms.txt 结构化校验
    if llms_resp and llms_resp[0] == 200 and llms_resp[1]:
        errors = _validate_llmstxt(llms_resp[1])
        print("\nllms.txt 结构校验:")
        if not errors:
            print("   ✅ 通过（# 标题 / > 摘要 / - [title](url) 列表 / URL 无重复）")
        else:
            for e in errors:
                print(f"   ❌ {e}")

    print("\n注：llms.txt 属于 GEO 生态实践，Google 官方明确不用于排名（见 ai-optimization-guide）。")
    return 0
