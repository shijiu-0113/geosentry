"""从 facts dict 生成深色主题单文件 HTML 审计报告。

结构对齐 docs/site-audit-hbyagada/audit-report.html：
  头部摘要卡片 → 一句话结论 → Top 优先级问题 → 全站分析 → 逐页明细表 →
  PDF 汇总 → P0/P1/P2 路线图

与原 gen_report.py 的区别：不硬编码站点叙事，全部从 facts dict 程序化推导。
纯标准库。
"""
from __future__ import annotations

import datetime
import html as html_lib
import re
from collections import Counter, defaultdict
from typing import Dict, List
from urllib.parse import urlparse


SEV_ORDER = {"critical": 0, "major": 1, "minor": 2}
SEV_LABEL = {"critical": "严重", "major": "重要", "minor": "次要"}


def esc(s) -> str:
    return html_lib.escape(str(s), quote=True)


def _short(url: str) -> str:
    p = urlparse(url).path or "/"
    return p


def _shorten(url: str, base: str) -> str:
    return url.replace(base.rstrip("/"), "") or "/"


def _aggregate_top_issues(facts: dict, base: str) -> List[dict]:
    """从 rows/flags 程序化推导 Top 优先级问题。
    返回 [{"sev": "critical|major|minor", "title": str, "detail_html": str}]。"""
    rows = facts["rows"]
    items: List[dict] = []

    # 1) 非 200 页面
    bad = [r for r in rows if r["status"] != 200]
    if bad:
        detail = "".join(
            f"<li><code>{esc(_short(r['url']))}</code> 状态码 {r['status']}"
            f"（{r.get('bytes', '?')}B，正文 {r.get('words', 0)} 词）</li>" for r in bad)
        items.append({"sev": "critical",
                      "title": f"{len(bad)} 个非 200 状态页面仍在站点索引中",
                      "detail_html": f"<ul class='tight'>{detail}</ul>",
                      "weight": len(bad)})

    # 2) canonical 指错组（簇级升级：≥3 页指向同一错误 URL → CRITICAL）
    canon_wrong_all = []
    canon_target_groups: Dict[str, list] = {}
    for r in rows:
        if r.get("canonical"):
            me = r["url"].rstrip("/")
            target = r["canonical"].rstrip("/")
            if target != me and target != r["url"]:
                canon_wrong_all.append(r)
                canon_target_groups.setdefault(r["canonical"], []).append(r)
    if canon_wrong_all:
        critical_clusters = {tgt: pages for tgt, pages in canon_target_groups.items()
                             if len(pages) >= 3}
        for tgt, pages in critical_clusters.items():
            paths = "、".join(f"<code>{esc(p['path'])}</code>" for p in pages[:8])
            more = f" 等 {len(pages)} 页" if len(pages) > 8 else ""
            items.append({
                "sev": "critical", "weight": len(pages),
                "title": f"{len(pages)} 个页面 canonical 集体错误指向 {_shorten(tgt, base)}",
                "detail_html": (
                    f"<p>涉及页面：{paths}{more}。</p>"
                    f"<p>这些页面的 &lt;link rel=canonical&gt; 全部指向 "
                    f"<code>{esc(_shorten(tgt, base))}</code>，等于主动向搜索引擎声明本页是副本，"
                    f"收录信号被自我销毁。</p>")})
        small_cluster_pages = [r for r in canon_wrong_all
                               if len(canon_target_groups.get(r["canonical"], [])) < 3]
        if small_cluster_pages:
            paths = "、".join(f"<code>{esc(r['path'])}</code>" for r in small_cluster_pages[:8])
            more = f" 等 {len(small_cluster_pages)} 页" if len(small_cluster_pages) > 8 else ""
            items.append({"sev": "major", "weight": len(small_cluster_pages),
                          "title": f"{len(small_cluster_pages)} 个页面 canonical 未自指（小簇/单页）",
                          "detail_html": f"<p>{paths}{more}。这些页面的 &lt;link rel=canonical&gt; 指向其他 URL。</p>"})

    # 2b) 孤儿核心页聚类（转化/工具类路径零入链 → CRITICAL）
    orphans = facts.get("orphans", [])
    CORE_PATHS = ("/rfq", "/quote", "/contact", "/products", "/spec-sheets",
                  "/query", "/ask", "/catalog", "/pricing", "/demo",
                  "/login", "/signup", "/checkout")
    core_orphans = []
    for o in orphans:
        if o["inbound"] <= 1:
            p = _shorten(o["url"], base).rstrip("/")
            if p in CORE_PATHS or any(p.startswith(cp + "/") for cp in CORE_PATHS):
                core_orphans.append(o)
    if core_orphans:
        paths = "、".join(
            f"<code>{esc(_shorten(o['url'], base))}</code>"
            + ("" if o["inbound"] == 0 else f" <span class='muted'>(入链{o['inbound']})</span>")
            for o in core_orphans[:12])
        items.append({
            "sev": "critical", "weight": len(core_orphans),
            "title": f"{len(core_orphans)} 个转化/工具核心页零入链（孤儿）",
            "detail_html": (
                f"<p>{paths}。这些页面通常是站点转化漏斗（询价/选型/产品列表/联系）的关键入口，"
                f"却在全站内部零入链或仅 1 条入链，爬虫难以发现、权重无法传递。</p>")})

    # 3) dup title / desc 簇
    for label, dup in (("title", facts.get("title_duplicates", {})),
                       ("meta description", facts.get("desc_duplicates", {}))):
        for dup_text, urls in dup.items():
            paths = "、".join(f"<code>{esc(_short(u))}</code>" for u in urls[:6])
            items.append({"sev": "major" if label == "title" else "minor",
                          "weight": len(urls),
                          "title": f"{len(urls)} 页 {label} 完全重复",
                          "detail_html": f"<p>重复字符串：<code>{esc(dup_text[:120])}</code></p>"
                                         f"<p>涉及页面：{paths}</p>"})

    # 4) 孤儿页（inbound=0）
    orphans = facts.get("orphans", [])
    zero_in = [o for o in orphans if o["inbound"] == 0]
    if zero_in:
        paths = "、".join(f"<code>{esc(_short(o['url']))}</code>" for o in zero_in[:12])
        more = f" 等 {len(zero_in)} 个零内链页" if len(zero_in) > 12 else ""
        items.append({"sev": "major", "weight": len(zero_in),
                      "title": f"{len(zero_in)} 个页面零内链（孤儿）",
                      "detail_html": f"<p>{paths}{more}。这些页面在全站内部无任何指向链接，"
                                     f"搜索引擎爬虫无法通过常规抓取发现它们。</p>"})

    # 5) 近似内容簇（jaccard >= 0.9）
    hi_sim = [p for p in facts.get("similar_top", []) if p["jaccard"] >= 0.9]
    if hi_sim:
        detail = "".join(
            f"<li><code>{esc(_shorten(p['a'], base))}</code> ↔ "
            f"<code>{esc(_shorten(p['b'], base))}</code> "
            f"<span class='score'>{p['jaccard']:.2f}</span></li>"
            for p in hi_sim[:12])
        more = f" 等 {len(hi_sim)} 对" if len(hi_sim) > 12 else ""
        items.append({"sev": "major", "weight": len(hi_sim),
                      "title": f"{len(hi_sim)} 对页面相似度 ≥ 0.9（doorway 风险）",
                      "detail_html": f"<ul class='tight'>{detail}</ul>"
                                     f"<p>{more}。这类高相似度页面存在被搜索引擎判定为批量生成薄内容的风险。</p>"})

    # 6) 系统性 title 超长
    long_title = [r for r in rows if r["status"] == 200 and r["title_len"] > 65]
    if long_title:
        worst = max((r["title_len"], r["path"]) for r in long_title)
        items.append({"sev": "major", "weight": len(long_title),
                      "title": f"{len(long_title)} 个 200 页 title 超 65 字符",
                      "detail_html": f"<p>最长 {worst[0]} 字符（<code>{esc(worst[1])}</code>）。"
                                     f"SERP 展示被截断、点击率受损，属模板级问题。</p>"})

    # 7) 正文偏薄
    thin = [r for r in rows if r["status"] == 200 and r["words"] < 300]
    if thin:
        paths = "、".join(f"<code>{esc(r['path'])}</code>" for r in thin[:8])
        items.append({"sev": "major", "weight": len(thin),
                      "title": f"{len(thin)} 个页面正文 &lt; 300 词",
                      "detail_html": f"<p>{paths}。</p>"})

    # 8) 无 H1
    no_h1 = [r for r in rows if r["h1_count"] == 0]
    if no_h1:
        paths = "、".join(f"<code>{esc(r['path'])}</code>" for r in no_h1[:8])
        items.append({"sev": "major", "weight": len(no_h1),
                      "title": f"{len(no_h1)} 个页面缺少 H1",
                      "detail_html": f"<p>{paths}。</p>"})

    # 9) 尾部斜杠双版本 200（MINOR）
    slash_duos = facts.get("trailing_slash_duos", [])
    if slash_duos:
        detail = "".join(
            f"<li><code>{esc(_shorten(d['without_slash'], base))}</code> ↔ "
            f"<code>{esc(_shorten(d['with_slash'], base))}</code></li>"
            for d in slash_duos[:8])
        items.append({"sev": "minor", "weight": len(slash_duos),
                      "title": f"{len(slash_duos)} 对 URL 带/不带末尾斜杠均返回 200",
                      "detail_html": f"<ul class='tight'>{detail}</ul>"
                                     f"<p>双版本并行会稀释收录信号，建议统一一种规范并用 301 收敛另一版本。</p>"})

    # 10) 在线探测发现的死链（内部 href 非 200）
    dead = facts.get("dead_links", [])
    if dead:
        detail = "".join(
            f"<li><code>{esc(_shorten(d['url'], base))}</code> 状态码 {d.get('status', '?')}"
            f"（{esc(d.get('error', '') or '')}）</li>" for d in dead[:10])
        more = f" 等 {len(dead)} 条" if len(dead) > 10 else ""
        sev = "major" if len(dead) <= 10 else "critical"
        items.append({"sev": sev, "weight": len(dead),
                      "title": f"{len(dead)} 条内部链接返回非 200（死链）",
                      "detail_html": f"<ul class='tight'>{detail}</ul>{more}"
                                     f"<p>这些链接从站内其他页面指向但目标不可达，浪费抓取预算并影响用户体验。</p>"})

    # TODO 5: 给每条补 weight（影响页数），同 severity 内按 weight 降序
    for it in items:
        it.setdefault("weight", 1)
    items.sort(key=lambda x: (SEV_ORDER[x["sev"]], -x["weight"]))
    return items[:12]


def _verdict(facts: dict, base: str) -> str:
    ic = facts["issues_count"]
    n_pages = len(facts["rows"])
    parts = []
    parts.append(f"站点共抓取 {n_pages} 个 HTML 页面，"
                 f"机器判定问题 {ic['critical']} 条 critical / {ic['major']} 条 major / {ic['minor']} 条 minor。")
    if ic["critical"]:
        parts.append(f"存在 {ic['critical']} 条 critical 级问题（阻止索引或主动误导），需立即修复。")
    else:
        parts.append("未发现 critical 级阻止索引问题。")
    if facts.get("orphans"):
        parts.append(f"共 {len(facts['orphans'])} 个入链 ≤1 的页面（孤儿页）。")
    if facts.get("similar_total"):
        parts.append(f"检测到 {facts['similar_total']} 对近似内容（Jaccard ≥ 0.5）。")
    return "".join(parts)


def _roadmap(facts: dict, top_issues: List[dict]) -> dict:
    """从 top_issues 自动分 P0/P1/P2。"""
    p0, p1, p2 = [], [], []
    for it in top_issues:
        line = f"{it['title']}"
        if it["sev"] == "critical":
            p0.append(line)
        elif it["sev"] == "major":
            p1.append(line)
        else:
            p2.append(line)
    if not p0:
        p0.append("检查 robots.txt 与 sitemap.xml 一致性，确认无 noindex 误封。")
    if not p1:
        p1.append("为全站 title/meta description 建立模板规范（50–65 字符 / 70–160 字符）。")
    if not p2:
        p2.append("补充 E-E-A-T 信号：作者实体链接、article:author meta、可见署名。")
    return {"p0": p0, "p1": p1, "p2": p2}


def render_report(facts: dict, site_url: str,
                  generated_at: str = None,
                  security_results: list = None,
                  sitemap_quality: dict = None,
                  image_summary: dict = None,
                  not_found: dict = None,
                  overall_score: dict = None,
                  psi_result: dict = None) -> str:
    """渲染完整 HTML 字符串。facts 由 site_audit.build_facts 产出。
    可选 extra：安全头/sitemap/图片/404 结果；离线时这些为 None，节区标注未采集。"""
    rows = facts["rows"]
    counts = facts["counts"]
    ic = facts["issues_count"]
    orphans = facts.get("orphans", [])
    pdfs = facts.get("pdfs", [])
    similar_top = facts.get("similar_top", [])
    base = site_url.rstrip("/")
    host = urlparse(site_url).netloc

    generated_at = generated_at or datetime.date.today().isoformat()

    # summary card numbers
    html_pages = counts.get("html", len(rows))
    pdf_n = counts.get("pdf", len(pdfs))
    crit = ic["critical"]; maj = ic["major"]; minor = ic["minor"]
    long_title_n = sum(1 for r in rows if r["title_len"] > 65 and r["status"] == 200)
    thin_n = sum(1 for r in rows if r["status"] == 200 and r["words"] < 700)
    dead_n = len(facts.get("dead_links", []))
    invalid_jsonld = sum(len(r.get("jsonld_invalid", [])) for r in rows)

    # per-page table
    tr_parts = []
    _muted_span = '<span class="muted">—</span>'
    for r in rows:
        flags = sorted(r.get("flags", []), key=lambda f: SEV_ORDER[f[0]])
        chip_html = "".join(
            f'<span class="chip c-{esc(sev)}" title="{esc(SEV_LABEL[sev])}">{esc(SEV_LABEL[sev])}·{esc(msg)}</span>'
            for sev, msg in flags)
        path = r["path"]
        st = r["status"]
        st_cls = "st-ok" if st == 200 else "st-bad"
        tl_cls = "num-bad" if r["title_len"] > 65 else ""
        w_cls = "num-bad" if (st == 200 and r["words"] < 700) else ""
        h1_cls = "num-bad" if r["h1_count"] == 0 else ""
        issues_cell = chip_html or _muted_span
        tr_parts.append(
            f'<tr><td class="col-url"><code>{esc(path)}</code></td>'
            f'<td class="col-num"><span class="badge {st_cls}">{st}</span></td>'
            f'<td class="col-num {tl_cls}">{r["title_len"]}</td>'
            f'<td class="col-num">{r["desc_len"]}</td>'
            f'<td class="col-num {w_cls}">{r["words"]}</td>'
            f'<td class="col-num {h1_cls}">{r["h1_count"]}</td>'
            f'<td class="col-issues">{issues_cell}</td></tr>')
    per_page_table = "\n".join(tr_parts)

    # PDF table
    pdf_rows = []
    for p in sorted(pdfs, key=lambda x: x["url"]):
        name = _shorten(p["url"], base)
        pdf_rows.append(
            f'<tr><td class="col-url"><code>{esc(name)}</code></td>'
            f'<td class="col-num"><span class="badge st-{"ok" if p["status"]==200 else "bad"}">{p["status"]}</span></td>'
            f'<td>{esc(p.get("content_type") or "—")}</td></tr>')
    pdf_table = "\n".join(pdf_rows)

    # orphans split
    zero_in = [o for o in orphans if o["inbound"] == 0]
    low_in = [o for o in orphans if o["inbound"] == 1]
    zero_in_html = "".join(f'<li><code>{esc(_shorten(o["url"], base))}</code></li>' for o in zero_in)
    low_in_html = "".join(
        f'<li><code>{esc(_shorten(o["url"], base))}</code> '
        f'<span class="muted">（仅 1 条入链，来自 {esc(", ".join(_shorten(x, base) or "/" for x in o["from"]))}）</span></li>'
        for o in low_in)

    # similar pairs
    sim_html = "".join(
        f'<li>{esc(_shorten(p["a"], base))} ↔ {esc(_shorten(p["b"], base))} '
        f'<span class="score">{p["jaccard"]:.2f}</span></li>'
        for p in similar_top[:26])

    # top issues auto
    top_issues = _aggregate_top_issues(facts, base)
    top_html = "".join(
        f'<li><span class="sev-tag s-{esc(it["sev"])}">{it["sev"].upper()}</span>'
        f'<strong>{esc(it["title"])}</strong><br/>{it["detail_html"]}</li>'
        for it in top_issues)

    # E. overall score card
    if overall_score:
        g = overall_score["grade"]
        g_color = {"A":"var(--ok)","B":"var(--ok)","C":"var(--min)",
                   "D":"var(--maj)","F":"var(--crit)"}.get(g, "var(--ink)")
        score_card = (
            f'<div class="card" style="border-top:3px solid {g_color}">'
            f'<div class="num" style="color:{g_color}">{g} · {overall_score["pct"]}分</div>'
            f'<div class="lbl">加权总分（{overall_score["earned"]}/{overall_score["total"]}）</div></div>')
    else:
        score_card = '<div class="card"><div class="num">—</div><div class="lbl">加权总分（离线未采集）</div></div>'

    # A. security headers section
    if security_results:
        sec_rows = "".join(
            f'<tr><td>{esc(r["name"])}</td>'
            f'<td><span class="badge st-{"ok" if r["passed"] else "bad"}">'
            f'{"Pass" if r["passed"] else "Fail"}</span></td>'
            f'<td class="muted">{esc(r["detail"][:80])}</td></tr>'
            for r in security_results)
        sec_section = (
            '<h3>3.5 技术与安全响应头</h3><div class="panel"><table>'
            '<thead><tr><th>检查项</th><th>结果</th><th>详情</th></tr></thead><tbody>'
            f'{sec_rows}</tbody></table></div>')
    else:
        sec_section = ('<h3>3.5 技术与安全响应头</h3><div class="panel">'
                       '<p class="muted">离线模式未采集响应头（需在线 --deep）。</p></div>')

    # F. sitemap quality section
    if sitemap_quality:
        sm_rows = "".join(
            f'<tr><td>{esc(c["key"])}</td>'
            f'<td><span class="badge st-{"ok" if c["passed"] else "bad"}">'
            f'{"Pass" if c["passed"] else "Fail"}</span></td>'
            f'<td class="muted">{esc(c["detail"])}</td></tr>'
            for c in sitemap_quality.get("checks", []))
        sm_section = (
            '<h3>3.6 sitemap 质量</h3><div class="panel"><table>'
            '<thead><tr><th>检查项</th><th>结果</th><th>详情</th></tr></thead><tbody>'
            f'{sm_rows}</tbody></table></div>')
    else:
        sm_section = ('<h3>3.6 sitemap 质量</h3><div class="panel">'
                      '<p class="muted">离线模式未采集 sitemap（需在线 --deep）。</p></div>')

    # G. image optimization section
    if image_summary and image_summary.get("total", 0) > 0:
        img_rows = "".join(
            f'<tr><td>{esc(c["key"])}</td>'
            f'<td><span class="badge st-{"ok" if c["passed"] else "bad"}">'
            f'{"Pass" if c["passed"] else "Fail"}</span></td>'
            f'<td class="muted">{esc(c["detail"])}</td></tr>'
            for c in image_summary.get("checks", []))
        img_section = (
            '<h3>3.7 图片优化（首页采样）</h3><div class="panel"><table>'
            '<thead><tr><th>检查项</th><th>结果</th><th>详情</th></tr></thead><tbody>'
            f'{img_rows}</tbody></table></div>')
    else:
        img_section = ('<h3>3.7 图片优化（首页采样）</h3><div class="panel">'
                       '<p class="muted">离线模式未采集图片（需在线 --deep）。</p></div>')

    # D. 404 section
    if not_found:
        nf = not_found
        soft_cls = "bad" if nf.get("soft_404") else "ok"
        nf_section = (
            '<h3>3.8 软 404 与自定义 404 页</h3><div class="panel"><ul class="tight">'
            f'<li>测试 URL：<code>{esc(nf.get("tested_url",""))}</code></li>'
            f'<li>HTTP 状态：{nf.get("status","?")} '
            f'<span class="badge st-{soft_cls}">{"软404!" if nf.get("soft_404") else "正常"}</span></li>'
            f'<li>404 页正文字数：{nf.get("body_len",0)}（&gt;200 为佳）</li>'
            f'<li>含回首页链接：{"是" if nf.get("has_home_link") else "否"}</li>'
            '</ul></div>')
    else:
        nf_section = ('<h3>3.8 软 404 与自定义 404 页</h3><div class="panel">'
                      '<p class="muted">离线模式未探测 404（需在线 --deep）。</p></div>')

    # H. PageSpeed Insights section (3.9)
    def _psival(v):
        return "-" if v is None else str(v)
    if psi_result and not psi_result.get("skipped"):
        cats = [("Performance", psi_result.get("performance")),
                ("Accessibility", psi_result.get("accessibility")),
                ("Best Practices", psi_result.get("best_practices")),
                ("SEO", psi_result.get("seo"))]
        cat_rows = "".join(
            f'<tr><td>{esc(k)}</td>'
            f'<td><span class="badge st-{"ok" if (v or 0) >= 90 else "bad"}">{_psival(v)}</span></td></tr>'
            for k, v in cats)
        metrics = [("LCP (ms)", psi_result.get("lcp_ms")),
                   ("CLS", psi_result.get("cls")),
                   ("FCP (ms)", psi_result.get("fcp_ms")),
                   ("TTFB (ms)", psi_result.get("ttfb_ms")),
                   ("INP (ms)", psi_result.get("inp_ms"))]
        met_rows = "".join(
            f'<tr><td>{esc(k)}</td><td>{_psival(v)}</td></tr>'
            for k, v in metrics)
        psi_section = (
            '<h3>3.9 PageSpeed Insights（mobile）</h3><div class="panel">'
            '<table><thead><tr><th>类别分</th><th>得分</th></tr></thead><tbody>'
            f'{cat_rows}</tbody></table>'
            '<table style="margin-top:10px"><thead><tr><th>核心 Web 指标</th><th>数值</th></tr></thead><tbody>'
            f'{met_rows}</tbody></table></div>')
    else:
        psi_note = (psi_result or {}).get("error", "")
        psi_section = (
            '<h3>3.9 PageSpeed Insights（mobile）</h3><div class="panel">'
            f'<p class="muted">PSI 未采集（{esc(psi_note) or "离线模式或无 API key（需在线 --deep）"}）。</p></div>')

    verdict = _verdict(facts, base)
    rm = _roadmap(facts, top_issues)
    p0_html = "".join(f"<li>{esc(x)}</li>" for x in rm["p0"])
    p1_html = "".join(f"<li>{esc(x)}</li>" for x in rm["p1"])
    p2_html = "".join(f"<li>{esc(x)}</li>" for x in rm["p2"])

    # dup clusters
    dup_clusters_html = ""
    for label, dup in (("title", facts.get("title_duplicates", {})),
                       ("meta description", facts.get("desc_duplicates", {}))):
        for dup_text, urls in dup.items():
            paths = "、".join(f"<code>{esc(_short(u))}</code>" for u in urls)
            dup_clusters_html += (f"<li>{len(urls)} 页 {label} 重复"
                                  f"（<code>{esc(dup_text[:100])}</code>）：{paths}</li>")
    if not dup_clusters_html:
        dup_clusters_html = "<li>未发现完全重复的 title 或 description。</li>"

    DOC = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(host)} 深度逐页 SEO/GEO 审计报告 · {esc(generated_at)}</title>
<style>
:root {{
  --bg:#0e141b; --panel:#161f29; --panel2:#1c2733; --line:#2a3846;
  --ink:#d7e0e8; --ink-dim:#8fa1b0; --accent:#5b8fb9; --steel:#7fa8c9;
  --crit:#e5534b; --maj:#e8923a; --min:#d8bc3e; --ok:#3f9d63;
}}
* {{ box-sizing:border-box; }}
html,body {{ margin:0; padding:0; }}
body {{
  background:var(--bg); color:var(--ink);
  font:14px/1.65 "Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  padding:32px 20px 80px;
  scrollbar-width: thin;
  scrollbar-color: rgba(91,143,185,0.4) transparent;
}}
body::-webkit-scrollbar {{ width:10px; }}
body::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.02); }}
body::-webkit-scrollbar-thumb {{
  background: linear-gradient(180deg, rgba(91,143,185,0.5), rgba(127,168,201,0.5));
  border-radius:99px;
  border:2px solid var(--bg);
}}
body::-webkit-scrollbar-thumb:hover {{
  background: linear-gradient(180deg, rgba(91,143,185,0.8), rgba(127,168,201,0.8));
}}
.wrap {{ max-width:1280px; margin:0 auto; }}
header.report-head {{
  border:1px solid var(--line); border-left:4px solid var(--crit);
  background:linear-gradient(180deg,var(--panel2),var(--panel));
  padding:26px 28px; margin-bottom:26px;
}}
h1 {{ font-size:24px; margin:0 0 6px; letter-spacing:.5px; }}
h1 .sub {{ color:var(--ink-dim); font-weight:400; font-size:14px; }}
h2 {{ font-size:19px; margin:38px 0 12px; padding-left:10px; border-left:3px solid var(--accent); }}
h3 {{ font-size:15px; margin:20px 0 8px; color:var(--steel); }}
p {{ margin:8px 0; }}
.muted {{ color:var(--ink-dim); }}
code {{
  background:#0b1118; border:1px solid var(--line); padding:1px 6px;
  border-radius:3px; font-family:Consolas,Menlo,monospace; font-size:12.5px;
  word-break:break-all;
}}
a {{ color:var(--steel); }}
.cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:16px 0; }}
@media(max-width:900px){{ .cards {{ grid-template-columns:repeat(2,1fr); }} }}
.card {{ background:var(--panel); border:1px solid var(--line); padding:14px 16px; border-radius:4px; }}
.card .num {{ font-size:26px; font-weight:700; line-height:1.1; }}
.card .lbl {{ color:var(--ink-dim); font-size:12px; margin-top:4px; }}
.card.crit {{ border-top:3px solid var(--crit); }} .card.crit .num {{ color:var(--crit); }}
.card.maj  {{ border-top:3px solid var(--maj);  }} .card.maj .num  {{ color:var(--maj); }}
.card.min  {{ border-top:3px solid var(--min);  }} .card.min .num  {{ color:var(--min); }}
.card.ok   {{ border-top:3px solid var(--ok);   }} .card.ok .num   {{ color:var(--ok); }}
ol.tops {{ padding-left:20px; }}
ol.tops > li {{ margin:14px 0; }}
.sev-tag {{ display:inline-block; font-size:11px; font-weight:700; padding:1px 8px; border-radius:3px; margin-right:8px; letter-spacing:1px; }}
.sev-tag.s-critical {{ background:rgba(229,83,75,.15); color:var(--crit); border:1px solid var(--crit); }}
.sev-tag.s-major    {{ background:rgba(232,146,58,.15);  color:var(--maj);  border:1px solid var(--maj); }}
.sev-tag.s-minor    {{ background:rgba(216,188,62,.15);  color:var(--min);  border:1px solid var(--min); }}
.panel {{ background:var(--panel); border:1px solid var(--line); padding:18px 20px; border-radius:4px; margin:12px 0; }}
ul.tight {{ margin:6px 0; padding-left:20px; }}
ul.tight li {{ margin:3px 0; }}
.score {{ color:var(--maj); font-weight:700; float:right; }}
.tablebox {{ overflow-x:auto; border:1px solid var(--line); border-radius:4px; }}
table {{ border-collapse:collapse; width:100%; table-layout:fixed; background:var(--panel); }}
col.c-url {{ width:26%; }} col.c-num {{ width:7%; }} col.c-issues {{ width:46%; }}
col.c-pdf {{ width:60%; }} col.c-st {{ width:12%; }} col.c-ct {{ width:28%; }}
th,td {{ padding:7px 9px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; word-wrap:break-word; }}
th {{ background:var(--panel2); font-size:12px; color:var(--ink-dim); letter-spacing:.5px; position:sticky; top:0; }}
tr:hover td {{ background:#1a2430; }}
.col-num {{ text-align:center; font-variant-numeric:tabular-nums; }}
.num-bad {{ color:var(--maj); font-weight:700; }}
.badge {{ display:inline-block; padding:0 6px; border-radius:3px; font-size:11px; font-weight:700; }}
.badge.st-ok {{ background:rgba(63,157,99,.15); color:var(--ok); }}
.badge.st-bad {{ background:rgba(229,83,75,.18); color:var(--crit); }}
.chip {{ display:inline-block; font-size:11px; padding:1px 6px; border-radius:3px; margin:1px 3px 1px 0; white-space:nowrap; }}
.chip.c-critical {{ background:rgba(229,83,75,.14); color:#f08a84; border:1px solid rgba(229,83,75,.5); }}
.chip.c-major    {{ background:rgba(232,146,58,.14);  color:#f0b478; border:1px solid rgba(232,146,58,.5); }}
.chip.c-minor    {{ background:rgba(216,188,62,.12);  color:#e6d27a; border:1px solid rgba(216,188,62,.45); }}
.road {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; }}
@media(max-width:900px){{ .road {{ grid-template-columns:1fr; }} }}
.road .panel {{ margin:0; }}
.road h3.p0 {{ color:var(--crit); }} .road h3.p1 {{ color:var(--maj); }} .road h3.p2 {{ color:var(--min); }}
.footer {{ margin-top:50px; color:var(--ink-dim); font-size:12px; border-top:1px solid var(--line); padding-top:14px; }}
</style>
</head>
<body>
<div class="wrap">

<header class="report-head">
  <h1>{esc(host)} 深度逐页 SEO / GEO 审计报告
    <span class="sub">— geosentry 自动生成</span></h1>
  <p class="muted">审计对象：<code>{esc(site_url)}</code>　|　审计日期：{esc(generated_at)}　|　引擎：geosentry.site_audit + geosentry.report_html</p>
</header>

<h2 id="summary">一、头部摘要</h2>
<div class="cards">
  <div class="card"><div class="num">{html_pages}</div><div class="lbl">已抓取 HTML 页面</div></div>
  <div class="card"><div class="num">{pdf_n}</div><div class="lbl">规格书 PDF</div></div>
  <div class="card crit"><div class="num">{crit}</div><div class="lbl">Critical 问题</div></div>
  <div class="card maj"><div class="num">{maj}</div><div class="lbl">Major 问题</div></div>
  <div class="card min"><div class="num">{minor}</div><div class="lbl">Minor 问题</div></div>
  <div class="card"><div class="num">{long_title_n}</div><div class="lbl">Title 超 65 字符的页面</div></div>
  <div class="card"><div class="num">{thin_n}</div><div class="lbl">正文 &lt;700 词的 200 页</div></div>
  <div class="card {'ok' if dead_n==0 and invalid_jsonld==0 else 'crit'}"><div class="num">{dead_n}/{invalid_jsonld}</div><div class="lbl">死链 / 无效 JSON-LD</div></div>
  {score_card}
</div>
<div class="panel">
  <p><strong>一句话结论：</strong>{verdict}</p>
</div>

<h2 id="top">二、必须立即修复的问题（Top 优先级）</h2>
<ol class="tops">
{top_html or "<li class='muted'>未检测到需要立即修复的问题。</li>"}
</ol>

<h2 id="sitewide">三、全站层面分析</h2>

<h3>3.1 重复 title / description 聚类</h3>
<div class="panel">
<ul class="tight">{dup_clusters_html}</ul>
</div>

<h3>3.2 近似内容簇（相似度 ≥ 0.5，Top 26）</h3>
<div class="panel">
<ul class="tight">{sim_html or "<li>未检测到高相似度页面对。</li>"}</ul>
</div>

<h3>3.3 孤儿页清单（入链 &le; 1）</h3>
<div class="panel">
<p><strong>零内链（inbound=0，共 {len(zero_in)} 个）：</strong></p>
<ul class="tight">{zero_in_html or "<li class='muted'>—</li>"}</ul>
<p><strong>仅 1 条入链（inbound=1，共 {len(low_in)} 个）：</strong></p>
<ul class="tight">{low_in_html or "<li class='muted'>—</li>"}</ul>
</div>

<h3>3.4 死链与 PDF 卫生</h3>
<div class="panel">
<ul class="tight">
<li>HTML 死链（非 200 且非 200 正常页）：{dead_n} 个。</li>
<li>PDF：共 {pdf_n} 个，{"全部 200" if all(p["status"]==200 for p in pdfs) else "存在非 200 项"}。</li>
</ul>
</div>

{sec_section}

{sm_section}

{img_section}

{nf_section}
{psi_section}

<h2 id="perpage">四、逐页明细表（全部 {html_pages} 个 HTML 页面）</h2>
<p class="muted">列说明：URL 短路径 ｜ HTTP 状态 ｜ title 字符数（&gt;65 标橙）｜ description 字符数 ｜ 正文词数（200 且 &lt;700 标橙）｜ H1 数量（0 标橙）｜ 关键问题标签。</p>
<div class="tablebox">
<table>
<colgroup><col class="c-url"><col class="c-num"><col class="c-num"><col class="c-num"><col class="c-num"><col class="c-num"><col class="c-issues"></colgroup>
<thead><tr><th>URL 短路径</th><th>HTTP</th><th>title 长度</th><th>desc 长度</th><th>正文词数</th><th>H1</th><th>关键问题</th></tr></thead>
<tbody>
{per_page_table}
</tbody>
</table>
</div>

<h2 id="pdf">五、PDF 状态汇总（共 {pdf_n} 个）</h2>
<div class="tablebox">
<table>
<colgroup><col class="c-pdf"><col class="c-st"><col class="c-ct"></colgroup>
<thead><tr><th>PDF 路径</th><th>状态</th><th>Content-Type</th></tr></thead>
<tbody>
{pdf_table or "<tr><td colspan='3' class='muted'>无 PDF 记录。</td></tr>"}
</tbody>
</table>
</div>

<h2 id="roadmap">六、按优先级排序的修复路线图</h2>
<div class="road">
  <div class="panel">
    <h3 class="p0">P0 · 立即（24–48 小时）</h3>
    <ul class="tight">{p0_html}</ul>
  </div>
  <div class="panel">
    <h3 class="p1">P1 · 本周内</h3>
    <ul class="tight">{p1_html}</ul>
  </div>
  <div class="panel">
    <h3 class="p2">本月内</h3>
    <ul class="tight">{p2_html}</ul>
  </div>
</div>

<div class="footer">
  本报告由 geosentry.site_audit + geosentry.report_html 自动生成；
  严重度口径：critical=阻止索引或主动误导；major=显著影响排名/转化；minor=体验/优化项。
</div>

</div>
</body>
</html>
"""
    return DOC
