"""逐页 SEO/GEO 审计分析：HTML 解析 + 跨页聚类 + 问题 flag 判定。

纯标准库。两种输入：
- 在线爬取产物（site_crawler.crawl_site 的 pages.json dict）
- 离线 raw/ 目录（load_raw_pages）：不联网，直接分析本地 HTML 文件

输出 facts dict（与 docs/site-audit-hbyagada/data/facts.json 同口径）：
  {counts, issues_count, rows, title_duplicates, desc_duplicates,
   similar_top, similar_total, orphans, dead_links, pdfs}
"""
from __future__ import annotations

import html as html_lib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urldefrag, urljoin, urlparse

from .site_crawler import slug

# 判定阈值（与样板 facts.json 对齐）
TITLE_MAX = 65
TITLE_MIN = 25
DESC_MAX = 170
DESC_MIN = 70
THIN_WORDS = 300
SHORT_WORDS = 600
THIN_REPORT = 700  # 报告里 <700 标橙
SIMILAR_THRESHOLD = 0.5
SIMILAR_LEN_DIFF = 120
ORPHAN_MAX_INBOUND = 1


# ------------------------------------------------------------- HTML parse --
class PageParser(HTMLParser):
    """从 HTML 提取 title/meta/link(canonical)/headings/images/links/JSON-LD/可见文本。"""

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self._in_title = False
        self.metas: Dict[str, str] = {}
        self.link_rels: Dict[str, List[str]] = {}
        self.canonical: Optional[str] = None
        self.headings: List[List] = []
        self.images: List[dict] = []
        self.ld_blocks: List[str] = []
        self._ld_buf: Optional[list] = None
        self._skip_depth = 0
        self._cur_h: Optional[Tuple[int, list]] = None
        self.visible_parts: List[str] = []
        self.hreflangs: List[dict] = []  # [{hreflang, href}]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self._skip_depth += 1
            if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
                self._ld_buf = []
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property") or a.get("http-equiv")
            if key:
                self.metas[key.lower()] = a.get("content", "")
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            href = a.get("href")
            if href:
                self.link_rels.setdefault(rel, []).append(href)
                if "canonical" in rel:
                    self.canonical = urljoin(self.base_url, href)
                if "alternate" in rel and a.get("hreflang"):
                    self.hreflangs.append({
                        "hreflang": a["hreflang"].strip(),
                        "href": urljoin(self.base_url, href),
                    })
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._cur_h = (int(tag[1]), [])
        elif tag == "img":
            src = a.get("src") or a.get("data-src") or ""
            self.images.append({
                "src": urljoin(self.base_url, src) if src else "",
                "alt": a.get("alt"),
            })

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            if self._ld_buf is not None and tag == "script":
                self.ld_blocks.append("".join(self._ld_buf))
                self._ld_buf = None
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._cur_h:
            lvl, buf = self._cur_h
            txt = re.sub(r"\s+", " ", "".join(buf)).strip()
            if txt:
                self.headings.append([lvl, txt])
            self._cur_h = None

    def handle_data(self, data):
        if self._skip_depth:
            if self._ld_buf is not None:
                self._ld_buf.append(data)
            return
        if self._in_title:
            self.title += data
        if self._cur_h is not None:
            self._cur_h[1].append(data)
        t = data.strip()
        if t:
            self.visible_parts.append(t)


def extract_links(html_text: str, base_url: str) -> List[dict]:
    """第二遍正则：可靠地把 <a href> 与 anchor 文本配对。"""
    links = []
    stack = []
    attr_href = re.compile(r"""href\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)
    attr_rel = re.compile(r"""rel\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)
    for m in re.finditer(r"<a\b([^>]*)>|</a>", html_text, re.I):
        if m.group(0).lower().startswith("</a"):
            if stack:
                href, start, rel = stack.pop()
                seg = html_text[start:m.start()]
                seg = re.sub(r"<[^>]+>", " ", seg)
                seg = html_lib.unescape(seg)
                seg = re.sub(r"\s+", " ", seg).strip()
                links.append({"href": urljoin(base_url, href), "anchor": seg, "rel": rel})
        else:
            attrs = m.group(1) or ""
            hm = attr_href.search(attrs)
            if hm:
                href = hm.group(2) or hm.group(3) or hm.group(4) or ""
                href = html_lib.unescape(href).strip()
                rm = attr_rel.search(attrs)
                rel = ""
                if rm:
                    rel = (rm.group(2) or rm.group(3) or rm.group(4) or "").lower()
                stack.append((href, m.end(), rel))
    return links


def parse_page(html_text: str, url: str, host: str) -> dict:
    """解析单页 HTML，返回 SEO 信号 dict。host 用于区分内链/外链。"""
    p = PageParser(url)
    p.feed(html_text)
    links = extract_links(html_text, url)
    title = re.sub(r"\s+", " ", p.title).strip()
    desc = p.metas.get("description", "").strip()
    robots = p.metas.get("robots", "").strip()
    viewport = p.metas.get("viewport", "").strip()
    og = {k: v for k, v in p.metas.items() if k.startswith("og:")}

    # JSON-LD 校验
    ld = []
    for raw in p.ld_blocks:
        raw_s = raw.strip()
        ok = True
        types: List[str] = []
        err = None
        try:
            obj = json.loads(raw_s)

            def walk(o):
                if isinstance(o, dict):
                    t = o.get("@type")
                    if t:
                        types.append(t if isinstance(t, str) else ",".join(t))
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(obj)
        except Exception as e:  # noqa: BLE001
            ok = False
            err = f"{type(e).__name__}: {e}"
        ld.append({"raw_len": len(raw_s), "valid": ok, "types": types, "error": err})

    visible = re.sub(r"\s+", " ", " ".join(p.visible_parts)).strip()
    words = re.findall(r"[A-Za-z0-9]+(?:[-./][A-Za-z0-9]+)*", visible)
    h1 = [t for l, t in p.headings if l == 1]
    levels = [l for l, _ in p.headings]
    heading_skip = False
    if levels:
        prev = levels[0]
        for l in levels[1:]:
            if l - prev > 1:
                heading_skip = True
            prev = l

    imgs = []
    missing_alt = 0
    empty_alt = 0
    for im in p.images:
        src = im["src"]
        if "data:" in src:
            continue
        alt = im["alt"]
        if alt is None:
            alt_state = "missing"
            missing_alt += 1
        elif alt.strip() == "":
            alt_state = "empty"
            empty_alt += 1
        else:
            alt_state = "ok"
        imgs.append({"src": src, "alt_state": alt_state, "alt": (alt or "")[:120]})

    out_links = []
    for l in links:
        u = urldefrag(l["href"])[0]
        if not u.startswith("http"):
            continue
        nh = urlparse(u).netloc
        out_links.append({
            "href": u, "anchor": l["anchor"][:100],
            "internal": (nh == host),
            "rel": l.get("rel", ""),
        })

    og_required = ["og:title", "og:description", "og:type", "og:url", "og:image"]
    og_missing = [k for k in og_required if k not in og]

    wl = [w.lower() for w in words]
    shingles = set()
    for i in range(len(wl) - 4):
        shingles.add(" ".join(wl[i:i + 5]))

    return {
        "title": title, "title_len": len(title),
        "description": desc, "desc_len": len(desc),
        "robots_meta": robots, "viewport": viewport,
        "canonical": p.canonical, "og": og, "og_missing": og_missing,
        "h1_count": len(h1), "h1_texts": h1,
        "heading_skip": heading_skip,
        "word_count": len(words), "visible_text_sample": visible[:400],
        "images": imgs, "missing_alt": missing_alt, "empty_alt": empty_alt,
        "img_total": len(imgs),
        "jsonld": ld, "links": out_links,
        "shingle_key": list(shingles)[:2000],
        "hreflangs": p.hreflangs,
    }


# ------------------------------------------------------------- cross-page --
def normalize_url(url: str) -> str:
    """M2.5: 剥离 utm_*/gclid/fbclid/sessionid 等追踪参数，用于 dup/近似判定。"""
    if not url:
        return url
    base, _, query = url.partition("?")
    if not query:
        return url
    kept = []
    for pair in query.split("&"):
        k = pair.split("=")[0].lower()
        if k.startswith("utm_") or k in ("gclid", "fbclid", "msclkid", "sessionid", "sid", "ref", "ref_src"):
            continue
        kept.append(pair)
    return base + ("?" + "&".join(kept) if kept else "")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b) if (a | b) else 0.0


def cross_page_analysis(pages: Dict[str, dict], host: str,
                        known_urls: Optional[set] = None) -> dict:
    """对已解析的 pages dict 做跨页分析：dup title/desc、近似内容、孤儿页。
    pages: {url: {"status", "final_url", "parsed": {...}}}
    known_urls: 站点全部 URL（sitemap），用于孤儿/死链判定；None 则用 pages 的 key。
    """
    html_urls = list(pages.keys())
    known_urls = known_urls or set(html_urls)

    # dup title / desc
    title_groups: Dict[str, list] = {}
    desc_groups: Dict[str, list] = {}
    for u, rec in pages.items():
        pr = rec.get("parsed") or {}
        t = _norm(pr.get("title", ""))
        d = _norm(pr.get("description", ""))
        if t:
            title_groups.setdefault(t, []).append(u)
        if d:
            desc_groups.setdefault(d, []).append(u)
    title_dups = {k: v for k, v in title_groups.items() if len(v) > 1}
    desc_dups = {k: v for k, v in desc_groups.items() if len(v) > 1}

    # near-duplicate content (jaccard on 5-word shingles)
    sh = {u: set((rec.get("parsed") or {}).get("shingle_key", []))
          for u, rec in pages.items() if rec.get("parsed")}
    keys = list(sh.keys())
    sim_pairs = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if abs(len(sh[a]) - len(sh[b])) > SIMILAR_LEN_DIFF:
                continue
            s = jaccard(sh[a], sh[b])
            if s >= SIMILAR_THRESHOLD:
                sim_pairs.append({"a": a, "b": b, "jaccard": round(s, 3)})
    sim_pairs.sort(key=lambda x: -x["jaccard"])

    # link graph → in-degree
    base = f"https://{host}"
    inbound: Dict[str, set] = {u: set() for u in html_urls}
    all_hrefs = set()
    for u, rec in pages.items():
        for l in (rec.get("parsed") or {}).get("links", []):
            if not l["internal"]:
                continue
            h = urldefrag(l["href"])[0]
            if h.rstrip("/") == base.rstrip("/"):
                h = base + "/"
            all_hrefs.add(h)
            if h in inbound:
                inbound[h].add(u)
    orphans = []
    for u in html_urls:
        n = len(inbound.get(u, set()))
        if n <= ORPHAN_MAX_INBOUND:
            orphans.append({"url": u, "inbound": n,
                            "from": sorted(inbound.get(u, set()))})

    # TODO 4: 尾部斜杠双版本 200 检出
    # 同一 path 带/不带末尾斜杠都在已抓集合里且状态都 200 → 双 URL 并行风险
    path_status = {urlparse(u).path: rec.get("status") for u, rec in pages.items()}
    slash_duos = []
    seen_duos = set()
    for path, st in path_status.items():
        if not path or path == "/":
            continue
        if path.endswith("/"):
            bare = path.rstrip("/")
            if bare in path_status and path_status[bare] == 200 and st == 200:
                key = (bare, path)
                if key not in seen_duos:
                    seen_duos.add(key)
                    slash_duos.append({"with_slash": base + path,
                                       "without_slash": base + bare})
        else:
            slashed = path + "/"
            if slashed in path_status and path_status[slashed] == 200 and st == 200:
                key = (path, slashed)
                if key not in seen_duos:
                    seen_duos.add(key)
                    slash_duos.append({"with_slash": base + slashed,
                                       "without_slash": base + path})

    # dead-link probe: internal hrefs not in known sitemap (offline 模式不联网，只列不探)
    probe = sorted({h for h in all_hrefs
                    if h.startswith(base)
                    and h not in known_urls
                    and not h.lower().endswith(".pdf")
                    and not h.startswith("mailto:")
                    and not h.startswith("javascript:")})
    # M1.1: hreflang 交叉校验
    hreflang_map: Dict[str, List[dict]] = {}  # url -> [{hreflang, href}]
    for u, rec in pages.items():
        hl = (rec.get("parsed") or {}).get("hreflangs") or []
        if hl:
            hreflang_map[u] = hl
    hreflang_issues = []
    # 双向回指校验：A 指 B 则 B 必须指 A
    for u, links in hreflang_map.items():
        for l in links:
            target = l["href"]
            target_rec = pages.get(target)
            if target_rec and target.rstrip("/") != u.rstrip("/"):
                target_links = hreflang_map.get(target, [])
                back_ref = any(t["href"].rstrip("/") == u.rstrip("/") for t in target_links)
                if not back_ref:
                    hreflang_issues.append({
                        "page": u, "hreflang": l["hreflang"],
                        "target": target,
                        "detail": f"{u} hreflang={l['hreflang']} 指向 {target}，但对方未回指",
                    })
    # x-default 检查：有 hreflang 的站点应有 x-default
    has_xdefault = any(
        l["hreflang"] == "x-default"
        for links in hreflang_map.values() for l in links
    )
    hreflang_xdefault_missing = bool(hreflang_map) and not has_xdefault

    # M2.2: Organization 名一致性
    org_names = set()
    for rec in pages.values():
        for ld in (rec.get("parsed") or {}).get("jsonld", []):
            if ld.get("valid") and isinstance(ld.get("data"), dict):
                d = ld["data"]
                t = d.get("@type", "")
                types = t if isinstance(t, list) else [t]
                if "Organization" in types and d.get("name"):
                    org_names.add(d["name"].strip())

    # M2.4: 锚文本分布
    generic_words = {"click here", "read more", "learn more", "more", "here", "link"}
    a_total = a_exact = a_generic = 0
    for rec in pages.values():
        for l in (rec.get("parsed") or {}).get("links", []):
            anchor = (l.get("anchor") or "").strip().lower()
            if not anchor:
                continue
            a_total += 1
            if anchor in generic_words:
                a_generic += 1
            elif len(anchor) > 15:
                a_exact += 1
    anchor_stats = {"total": a_total, "exact": a_exact, "generic": a_generic,
                    "exact_pct": round(a_exact / a_total * 100, 1) if a_total else 0,
                    "generic_pct": round(a_generic / a_total * 100, 1) if a_total else 0}

    return {
        "title_duplicates": title_dups,
        "desc_duplicates": desc_dups,
        "similar_pairs": sim_pairs,
        "orphans": orphans,
        "dead_links": [],
        "unknown_internal_hrefs": probe,
        "trailing_slash_duos": slash_duos,
        "hreflang_issues": hreflang_issues,
        "hreflang_xdefault_missing": hreflang_xdefault_missing,
        "org_names": sorted(org_names),
        "anchor_stats": anchor_stats,
    }


# ------------------------------------------------------------- flagging ----
def flag_page(u: str, rec: dict) -> List[Tuple[str, str]]:
    """单页问题 flag 判定（与 summarize.py 同口径）。返回 [(severity, message)]。"""
    pr = rec.get("parsed") or {}
    flags: List[Tuple[str, str]] = []
    st = rec.get("status")
    if st != 200:
        flags.append(("critical", f"HTTP {st}"))
    if rec.get("final_url") and rec["final_url"].rstrip("/") != u.rstrip("/"):
        flags.append(("major", f"redirected -> {rec['final_url']}"))
    # M1.2: 重定向链检查
    chain = rec.get("redirect_chain") or []
    if len(chain) > 3:
        flags.append(("minor", f"重定向链过长 ({len(chain)} 跳)"))
    for _, code in chain:
        if code in (302, 307):
            flags.append(("major", f"重定向 {code} 应改用 301（永久）"))
            break
    if chain and not chain[-1][0].startswith("https://"):
        flags.append(("minor", "重定向链尾非 HTTPS"))
    title = pr.get("title", "")
    if not title:
        flags.append(("critical", "缺少 title"))
    elif pr.get("title_len", 0) > TITLE_MAX:
        flags.append(("major", f"title 过长 {pr['title_len']} 字符"))
    elif pr.get("title_len", 0) < TITLE_MIN:
        flags.append(("minor", f"title 过短 {pr['title_len']} 字符"))
    desc = pr.get("description", "")
    if not desc:
        flags.append(("major", "缺少 meta description"))
    elif pr.get("desc_len", 0) > DESC_MAX:
        flags.append(("minor", f"description 过长 {pr['desc_len']}"))
    elif pr.get("desc_len", 0) < DESC_MIN:
        flags.append(("minor", f"description 过短 {pr['desc_len']}"))
    h1c = pr.get("h1_count", 0)
    if h1c == 0:
        flags.append(("major", "无 H1"))
    elif h1c > 1:
        flags.append(("major", f"多个 H1 ({h1c})"))
    wc = pr.get("word_count", 0)
    if wc < THIN_WORDS:
        flags.append(("major", f"正文偏薄 ~{wc} 词"))
    elif wc < SHORT_WORDS:
        flags.append(("minor", f"正文较短 ~{wc} 词"))
    if not pr.get("canonical"):
        flags.append(("critical", "缺少 canonical"))
    else:
        c = pr["canonical"].rstrip("/")
        me = u.rstrip("/")
        if c != me and c != u:
            flags.append(("major", f"canonical 指向 {pr['canonical']}（自我指向？）"))
    robots = pr.get("robots_meta", "")
    if "noindex" in robots:
        flags.append(("critical", f"meta robots=noindex ({robots})"))
    if not pr.get("viewport"):
        flags.append(("major", "缺 viewport"))
    if pr.get("missing_alt", 0) > 0:
        flags.append(("major", f"{pr['missing_alt']} 张图缺 alt"))
    if pr.get("heading_skip"):
        flags.append(("minor", "标题层级跳级"))
    LD_REQUIRED = {
        "Product": ["name", "offers"],
        "Organization": ["name", "url"],
        "BreadcrumbList": ["itemListElement"],
        "FAQPage": ["mainEntity"],
        "Article": ["headline", "author"],
    }
    for ld in pr.get("jsonld", []):
        if not ld["valid"]:
            flags.append(("critical", f"JSON-LD 语法错误: {ld['error']}"))
            continue
        graph = ld.get("data") or {}
        types = graph.get("@type", [])
        if isinstance(types, str):
            types = [types]
        for t in (types if isinstance(types, list) else [types]):
            req = LD_REQUIRED.get(t)
            if req:
                missing = [k for k in req if k not in graph]
                if missing:
                    sev = "critical" if t == "Product" and "offers" in missing else "major"
                    flags.append((sev, f"JSON-LD {t} 缺必填属性: {','.join(missing)}"))
    if pr.get("og_missing"):
        flags.append(("minor", f"OG 缺 {','.join(pr['og_missing'])}"))
    # M1.1: hreflang 检查（单页级；交叉回指在 cross_page_analysis）
    hls = pr.get("hreflangs") or []
    if hls and not any(l["hreflang"] == "x-default" for l in hls):
        flags.append(("major", "hreflang 缺少 x-default 声明"))
    return flags


def build_facts(pages: Dict[str, dict], host: str,
                counts: dict, pdfs: list, cross: Optional[dict] = None) -> dict:
    """把爬取/离线解析结果压成 facts dict（与 facts.json 同口径）。"""
    if cross is None:
        cross = cross_page_analysis(pages, host)
    issues_count = {"critical": 0, "major": 0, "minor": 0}
    rows = []
    for u, rec in pages.items():
        pr = rec.get("parsed") or {}
        flags = flag_page(u, rec)
        for sev, _ in flags:
            issues_count[sev] += 1
        rows.append({
            "url": u,
            "path": urlparse(u).path or "/",
            "status": rec.get("status"),
            "bytes": rec.get("bytes"),
            "ms": rec.get("load_ms"),
            "title": pr.get("title", ""),
            "title_len": pr.get("title_len", 0),
            "desc": pr.get("description", ""),
            "desc_len": pr.get("desc_len", 0),
            "h1_count": pr.get("h1_count", 0),
            "h1_texts": pr.get("h1_texts", []),
            "words": pr.get("word_count", 0),
            "canonical": pr.get("canonical"),
            "robots": pr.get("robots_meta", ""),
            "viewport": bool(pr.get("viewport")),
            "imgs": pr.get("img_total", 0),
            "missing_alt": pr.get("missing_alt", 0),
            "empty_alt": pr.get("empty_alt", 0),
            "jsonld_types": [t for b in pr.get("jsonld", []) for t in b["types"]],
            "jsonld_invalid": [b["error"] for b in pr.get("jsonld", []) if not b["valid"]],
            "og_missing": pr.get("og_missing", []),
            "flags": flags,
            "n_links": len(pr.get("links", [])),
        })
    rows.sort(key=lambda r: (0 if any(f[0] == "critical" for f in r["flags"]) else 1, r["path"]))
    return {
        "counts": counts,
        "issues_count": issues_count,
        "rows": rows,
        "title_duplicates": cross["title_duplicates"],
        "desc_duplicates": cross["desc_duplicates"],
        "similar_top": cross["similar_pairs"][:40],
        "similar_total": len(cross["similar_pairs"]),
        "orphans": cross["orphans"],
        "dead_links": cross.get("dead_links", []),
        "pdfs": pdfs,
        "trailing_slash_duos": cross.get("trailing_slash_duos", []),
    }


# ------------------------------------------------------------- offline ----
def _url_from_html_or_slug(text: str, fname: str, base_url: str) -> str:
    """离线模式：优先用文件名反推 URL（文件名由 site_crawler.slug 生成，
    是 ground truth——即使页面 canonical 指错，文件名仍指向真实路径）；
    若文件名不遵循 slug 约定（含原 `_` 等无法反推），退而求其次用 canonical/og:url。"""
    stem = Path(fname).stem
    # 1) 文件名反推：slug 把所有非 [a-zA-Z0-9._-] 替换成 _，原 / 都变成 _
    #    反推：把 _ 替换回 /；home -> /
    if stem == "home":
        return base_url.rstrip("/") + "/"
    inferred_path = "/" + stem.replace("_", "/")
    inferred_url = base_url.rstrip("/") + inferred_path
    # 2) canonical 校验：若 canonical 存在且路径与反推一致（仅末尾斜杠差异），用反推
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
                  text, re.I)
    canon = None
    if m:
        canon = urldefrag(m.group(1).strip())[0]
    if canon:
        canon_path = urlparse(canon).path or "/"
        # canonical 自指（与反推路径一致）：用反推 URL（避免重定向/末尾斜杠差异）
        if canon_path.rstrip("/") == inferred_path.rstrip("/"):
            return inferred_url
        # canonical 指向别处（canonical 指错 bug）：仍用反推 URL（文件名是真相）
        return inferred_url
    return inferred_url


def load_raw_pages(raw_dir: Path, base_url: str) -> Dict[str, dict]:
    """离线模式：扫描 raw_dir/*.html，解析每页，返回 pages dict。
    每页 status=200（离线都视为已抓成功），url 从 canonical/og:url/文件名反推。"""
    host = urlparse(base_url).netloc
    pages: Dict[str, dict] = {}
    for f in sorted(raw_dir.glob("*.html")):
        text = f.read_text(encoding="utf-8", errors="replace")
        url = _url_from_html_or_slug(text, f.name, base_url)
        try:
            parsed = parse_page(text, url, host)
        except Exception as e:  # noqa: BLE001
            pages[url] = {"url": url, "final_url": url, "status": 200,
                          "error": f"parse: {e}", "load_ms": 0,
                          "content_type": "text/html", "bytes": f.stat().st_size}
            continue
        pages[url] = {
            "url": url, "final_url": url, "status": 200, "error": None,
            "load_ms": 0, "content_type": "text/html",
            "bytes": f.stat().st_size, "parsed": parsed,
        }
    return pages


def scan_local_pdfs(pdf_dir: Path, base_url: str) -> list:
    """离线 PDF 卫生检查：扫描 pdf_dir/*.pdf，读文件头 b'%PDF-' 判有效性。"""
    out = []
    if not pdf_dir.exists():
        return out
    for f in sorted(pdf_dir.glob("*.pdf")):
        head = f.read_bytes()[:5]
        valid = head == b"%PDF-"
        out.append({
            "url": f"{base_url.rstrip('/')}/pdfs/{f.name}",
            "status": 200 if valid else 500,
            "final_url": f"{base_url.rstrip('/')}/pdfs/{f.name}",
            "content_type": "application/pdf" if valid else "application/octet-stream",
            "content_length": str(f.stat().st_size),
            "error": None if valid else "corrupt header",
        })
    return out


def audit_offline(raw_dir: Path, base_url: str, pdfs: Optional[list] = None) -> dict:
    """离线审计入口：分析 raw_dir 下全部 HTML，产出 facts dict。
    若 raw_dir 同级存在 pdf/ 目录，自动扫描 PDF 文件头做卫生检查。"""
    pages = load_raw_pages(raw_dir, base_url)
    host = urlparse(base_url).netloc
    if pdfs is None:
        # TODO 2: 自动发现 raw_dir 同级的 pdf/ 目录
        pdf_dir = raw_dir.parent / "pdf"
        pdfs = scan_local_pdfs(pdf_dir, base_url)
    counts = {"unique": len(pages), "html": len(pages), "pdf": len(pdfs)}
    cross = cross_page_analysis(pages, host)
    return build_facts(pages, host, counts, pdfs, cross)



# ============================================================
# F. sitemap 质量检查
# ============================================================

PRIVACY_LEGAL_PATHS = ("/privacy", "/terms", "/legal", "/cookies",
                       "/gdpr", "/privacy-policy", "/terms-of-service")


def analyze_sitemap_quality(sitemap_xml: str, robots_txt: str,
                           known_urls: list) -> dict:
    """F: sitemap 质量检查（纯文本/正则，不引入 xml.etree 之外）。
    返回 {xml_valid, has_url_entries, has_lastmod, robots_declares_sitemap,
          privacy_leaked: [url, ...], checks: [{key, passed, detail}]}
    """
    checks = []
    # XML 有效（宽松判定：含 <?xml 或 <urlset 或 <sitemapindex）
    xml_valid = bool(re.search(r"<\?xml|<urlset|<sitemapindex", sitemap_xml, re.I))
    checks.append({"key": "xml_valid", "passed": xml_valid,
                   "detail": "包含 XML 声明或 <urlset>" if xml_valid else "无 XML 结构"})

    # 含 <url> 条目
    locs = re.findall(r"<loc>([^<]+)</loc>", sitemap_xml, re.I)
    has_urls = len(locs) > 0
    checks.append({"key": "has_url_entries", "passed": has_urls,
                   "detail": f"发现 {len(locs)} 个 <loc>" if has_urls else "无 <loc> 条目"})

    # 有 <lastmod>
    has_lastmod = bool(re.search(r"<lastmod>", sitemap_xml, re.I))
    checks.append({"key": "has_lastmod", "passed": has_lastmod,
                   "detail": "至少一个 URL 含 <lastmod>" if has_lastmod else "未见 <lastmod>"})

    # robots.txt 声明 sitemap
    robots_sm = bool(re.search(r"(?i)^sitemap:\s*\S+", robots_txt, re.M))
    checks.append({"key": "robots_declares_sitemap", "passed": robots_sm,
                   "detail": "robots.txt 含 Sitemap: 指令" if robots_sm else "robots.txt 未声明 Sitemap"})

    # 隐私/法律页不应出现在 sitemap
    privacy_leaked = []
    for loc in locs:
        for pat in PRIVACY_LEGAL_PATHS:
            if pat in loc.lower():
                privacy_leaked.append(loc)
                break
    checks.append({"key": "no_privacy_in_sitemap", "passed": len(privacy_leaked) == 0,
                   "detail": f"{len(privacy_leaked)} 个隐私/法律页出现在 sitemap" if privacy_leaked else "无隐私页泄露"})

    return {
        "xml_valid": xml_valid,
        "has_url_entries": has_urls,
        "has_lastmod": has_lastmod,
        "robots_declares_sitemap": robots_sm,
        "privacy_leaked": privacy_leaked,
        "loc_count": len(locs),
        "checks": checks,
    }


# ============================================================
# G. 图片优化检查（逐页）
# ============================================================

def analyze_images(html_text: str, base_url: str) -> dict:
    """G: 从 HTML 中提取 <img> 标签并做启发式优化检查。
    返回 {total, has_dimensions, uses_modern_format, lazy_after_first,
          has_fetchpriority, has_alt, checks: [...]}
    """
    # 提取 <img ...> 标签
    img_tags = re.findall(r"<img\b[^>]*>", html_text, re.I)
    total = len(img_tags)
    if total == 0:
        return {"total": 0, "checks": [], "has_dimensions": False,
                "uses_modern_format": False, "lazy_after_first": True,
                "has_fetchpriority": False, "has_alt": True}

    with_dim = 0
    modern_fmt = 0
    lazy_count = 0
    has_fp = False
    with_alt = 0
    for i, tag in enumerate(img_tags):
        if re.search(r'\b(width|height)\s*=', tag, re.I):
            with_dim += 1
        # src/srcset 含 webp/avif
        if re.search(r"(webp|avif)", tag, re.I):
            modern_fmt += 1
        # 非首图 lazy
        if i > 0 and re.search(r'\bloading\s*=\s*"lazy"', tag, re.I):
            lazy_count += 1
        if re.search(r'\bfetchpriority\s*=\s*"high"', tag, re.I):
            has_fp = True
        if re.search(r'\balt\s*=\s*"[^"]+"', tag, re.I) or re.search(r"\balt\s*=\s*'[^']+'", tag, re.I):
            with_alt += 1

    expected_lazy = max(0, total - 1)  # 非首图应 lazy
    return {
        "total": total,
        "has_dimensions": with_dim == total,
        "uses_modern_format": modern_fmt > 0,
        "lazy_after_first": lazy_count >= expected_lazy,
        "has_fetchpriority": has_fp,
        "has_alt": with_alt == total,
        "with_dimensions": with_dim,
        "modern_format_count": modern_fmt,
        "lazy_count": lazy_count,
        "with_alt": with_alt,
        "checks": [
            {"key": "img_dimensions", "passed": with_dim == total,
             "detail": f"{with_dim}/{total} 张图声明 width/height"},
            {"key": "img_modern_format", "passed": modern_fmt > 0,
             "detail": f"{modern_fmt} 张图使用 WebP/AVIF"},
            {"key": "img_lazy", "passed": lazy_count >= expected_lazy,
             "detail": f"{lazy_count}/{expected_lazy} 张非首图 loading=lazy"},
            {"key": "img_fetchpriority", "passed": has_fp,
             "detail": "首图/LCP 图 fetchpriority=high" if has_fp else "未见 fetchpriority=high"},
            {"key": "img_alt", "passed": with_alt == total,
             "detail": f"{with_alt}/{total} 张图有 alt"},
        ],
    }
