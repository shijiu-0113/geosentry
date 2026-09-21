"""命令行入口：python -m geosentry <子命令>

子命令：
    index              从 corpus/ 重建索引（幂等）
    search "<问题>"    检索知识库，返回带出处结果
    info               显示索引状态
    audit --url <site> 站点 GEO/SEO 基础审计（对照本地知识库）
    crawl --source <s> 增量爬取语料（调用 scripts/crawl_docs.py，需网络）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _print_results(results: list, top_k: int) -> None:
    print(f"\n命中 {len(results)} 条（top {top_k}）：\n")
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['doc']}  (score 相关度来源: {r['source']})")
        if r.get("url"):
            print(f"    出处: {r['url']}")
        if r.get("heading"):
            print(f"    章节: {r['heading']}")
        text = r["text"].replace("\n", " ")
        print(f"    片段: {text[:180]}{'...' if len(text) > 180 else ''}\n")


def cmd_index(args) -> int:
    from . import GeoSentry
    bp = GeoSentry(data_dir=Path(args.data_dir) if args.data_dir else None)
    meta = bp.index()
    print(f"索引完成：{meta['n_chunks']} chunks / {meta['doc_count']} 文档 / "
          f"后端 {meta['backend']} → {bp.data_dir}")
    return 0


def cmd_search(args) -> int:
    from . import GeoSentry
    bp = GeoSentry(data_dir=Path(args.data_dir) if args.data_dir else None)
    if not bp.info()["indexed"]:
        print("尚未建立索引，请先运行: python -m geosentry index")
        return 1
    if not args.query or not args.query.strip():
        print("查询不能为空，请提供一个非空的问题。")
        return 2
    if args.top_k is not None and args.top_k < 1:
        print("--top-k 必须 >= 1")
        return 2
    results = bp.search(args.query, top_k=args.top_k)
    _print_results(results, args.top_k)
    return 0


def cmd_info(args) -> int:
    from . import GeoSentry
    bp = GeoSentry(data_dir=Path(args.data_dir) if args.data_dir else None)
    print(json.dumps(bp.info(), ensure_ascii=False, indent=2))
    return 0


def cmd_audit(args) -> int:
    if getattr(args, "deep", False):
        return _cmd_audit_deep(args)
    from .geo_audit import run_audit
    return run_audit(args.url, top_k=args.top_k, verify_ssl=not args.no_verify_ssl)


def _cmd_audit_deep(args) -> int:
    """全站逐页深审：爬取（或离线分析 raw/）→ facts → HTML 报告。"""
    import json as _json
    from pathlib import Path as _P
    out_dir = _P(args.out) if args.out else _P("docs") / "site-audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / "data"
    data_dir.mkdir(exist_ok=True)

    # 在线模式才会填充的新检查结果（离线保持 None → 报告占位）
    security_results = sitemap_quality = image_summary = not_found = None

    if args.offline:
        # 离线模式：直接分析本地 raw 目录，不联网
        from .site_audit import audit_offline
        raw_dir = _P(args.offline)
        print(f"[offline] analyzing {raw_dir} ...")
        facts = audit_offline(raw_dir, args.url)
        pages_payload = {"site": args.url, "counts": facts["counts"],
                         "pages": {}}
        (data_dir / "facts.json").write_text(
            _json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[offline] facts.json: {len(facts['rows'])} pages, "
              f"issues={facts['issues_count']}")
    else:
        # 在线模式：爬取
        from .site_crawler import (crawl_site, fetch_sitemap, fetch_robots,
                                  bfs_discover, probe_dead_links)
        from .site_audit import (build_facts, cross_page_analysis)
        print(f"[deep] crawling {args.url} ...")

        # --bfs / --bfs-fallback：先解析 sitemap，按需 BFS 合并
        delay_s = args.delay or 1.2
        if getattr(args, "rate", None):
            delay_s = 1.0 / float(args.rate)
        ua = "Mozilla/5.0 (compatible; geosentry-audit/1.0)"
        if getattr(args, "ua", "fixed") == "rotate" and getattr(args, "concurrency", 1) > 1:
            ua = "Mozilla/5.0 (compatible; geosentry-audit/%d)" % (1 % 5)
        cache = None
        if getattr(args, "cache", "on") != "off":
            from .cache import DiskCache
            cache = DiskCache(out_dir / ".cache", enabled=True)
        verify = not args.no_verify_ssl
        robots_txt = fetch_robots(args.url, timeout=15)
        sm_urls = fetch_sitemap(args.url, timeout=15)
        merged = list(sm_urls)
        use_bfs = bool(getattr(args, "bfs", False))
        bfs_fb = bool(getattr(args, "bfs_fallback", True))
        if use_bfs or (bfs_fb and not sm_urls):
            why = "explicit --bfs" if use_bfs else "sitemap empty, fallback"
            print(f"[deep] BFS discovery ({why}) ...")
            bfs_urls = bfs_discover(args.url, robots_txt=robots_txt,
                                    delay=delay_s, verify_ssl=verify,
                                    max_pages=args.max_pages or 100)
            seen = set(merged)
            for u in bfs_urls:
                if u not in seen:
                    merged.append(u)
                    seen.add(u)
            print(f"       sitemap={len(sm_urls)} + bfs={len(bfs_urls)} → merged={len(merged)}")
        result = crawl_site(args.url, out_dir,
                            delay=delay_s,
                            verify_ssl=verify,
                            max_pages=args.max_pages,
                            pre_discovered_urls=merged,
                            concurrency=getattr(args, "concurrency", 1),
                            cache=cache,
                            render_mode=getattr(args, "render", "off"))
        # parse each HTML page
        from .site_audit import parse_page
        from urllib.parse import urlparse
        host = urlparse(args.url).netloc
        pages = result["pages"]
        for u, rec in pages.items():
            raw_file = out_dir / "raw" / (u.rstrip("/").split("/")[-1] or "home")
            # find saved raw html
            from .site_crawler import slug
            raw_file = out_dir / "raw" / (slug(u) + ".html")
            if raw_file.exists():
                raw_html = raw_file.read_text(encoding="utf-8", errors="replace")
                rec["parsed"] = parse_page(raw_html, u, host)
                # content_filter 只补充主文本（喂 RAG），不替换 parse_page 输入
                cf = getattr(args, "content_filter", "none")
                if cf and cf != "none":
                    try:
                        from .content_extract import extract_main_content
                        rec["parsed"]["main_text"] = extract_main_content(raw_html, cf)
                    except Exception:
                        pass
        cross = cross_page_analysis(pages, host)
        # 在线死链探测——对 unknown_internal_hrefs 主动 GET
        probes = cross.get("unknown_internal_hrefs", [])
        if probes:
            max_p = getattr(args, "max_dead_probes", 50)
            print(f"[deep] probing {len(probes)} unknown internal hrefs (max {max_p}) ...")
            external_probes = probes
            if getattr(args, "external_probe", False):
                ext = {l["href"] for pg in pages for l in pg.get("links", []) if not l.get("internal")}
                external_probes = probes + sorted(ext)
            cross["dead_links"] = probe_dead_links(
                external_probes, robots_txt=robots_txt,
                delay=args.delay or 1.2,
                verify_ssl=not args.no_verify_ssl,
                external=getattr(args, "external_probe", False),
                base_url=args.url,
                max_probes=max_p)
            print(f"       dead links found: {len(cross['dead_links'])}")
        facts = build_facts(pages, host, result["counts"], result["pdfs"], cross)
        (data_dir / "facts.json").write_text(
            _json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
        (data_dir / "pages.json").write_text(
            _json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

        # 在线模式：跑新增检查项并采样
        from .site_security import analyze_security_headers
        from .site_audit import analyze_sitemap_quality, analyze_images
        from .site_crawler import probe_404, http_get
        from .scoring import compute_overall_score

        # A. 安全头：采样首页响应头
        try:
            home_res = http_get(args.url, ua=args._ua if hasattr(args, "_ua") else "geosentry/0.1",
                                timeout=15, delay=0, verify_ssl=verify)
            security_results = analyze_security_headers(dict(home_res.headers))
            print(f"[deep] security headers: {sum(1 for r in security_results if r['passed'])}/{len(security_results)} pass")
        except Exception as e:
            print(f"[deep] security headers skipped: {e}")

        # F. sitemap 质量：用已抓的 sitemap 文本
        try:
            sm_text = ""
            # 从 result 里找 sitemap 文本（crawl_site 没存，重新拉一次）
            from .site_crawler import fetch_sitemap as _fs
            # analyze_sitemap_quality 需要原始 XML；fetch_sitemap 只返回 URL 列表
            # 这里用 merged URL 列表做启发式检查
            sm_quality = analyze_sitemap_quality("", robots_txt, merged)
            sitemap_quality = sm_quality
        except Exception as e:
            print(f"[deep] sitemap quality skipped: {e}")

        # G. 图片优化：采样首页 HTML
        try:
            home_url = args.url.rstrip("/") + "/"
            if home_url in pages and pages[home_url].get("parsed"):
                home_html = pages[home_url]["parsed"].get("_raw_html", "")
            else:
                home_html = ""
            if not home_html:
                # 重新读首页 raw 文件
                from .site_crawler import slug as _slug
                home_raw = out_dir / "raw" / (_slug(home_url) + ".html")
                if home_raw.exists():
                    home_html = home_raw.read_text(encoding="utf-8", errors="replace")
            image_summary = analyze_images(home_html, args.url)
            print(f"[deep] images: {image_summary.get('total', 0)} on homepage")
        except Exception as e:
            print(f"[deep] image analysis skipped: {e}")

        # D. 软 404 探测
        try:
            not_found = probe_404(args.url, delay=delay_s, verify_ssl=verify)
            print(f"[deep] 404 probe: soft={not_found['soft_404']} body_len={not_found['body_len']}")
        except Exception as e:
            print(f"[deep] 404 probe skipped: {e}")

        # M1.4: PSI (PageSpeed Insights) — 无 key/无网时优雅降级
        psi_result = None
        try:
            print("[deep] PSI: connecting to Google (6s timeout, skip if unreachable) ...")
            from .site_external import run_pagespeed
            psi_result = run_pagespeed(args.url)
            if psi_result.get("skipped"):
                print(f"[deep] PSI skipped: {psi_result.get('error', '')}")
            else:
                print(f"[deep] PSI: perf={psi_result.get('performance')} "
                      f"inp={psi_result.get('inp_ms')}ms")
        except Exception as e:
            print(f"[deep] PSI skipped: {e}")

        # E. 加权总分
        overall_score = compute_overall_score(
            security_results=security_results,
            sitemap_checks=(sitemap_quality or {}).get("checks"),
            image_checks=(image_summary or {}).get("checks"),
            not_found_result=not_found,
            psi_result=psi_result)
        print(f"[deep] overall score: {overall_score['pct']} ({overall_score['grade']})")

    # render report
    from .report_html import render_report
    # 离线模式下 security_results 等仍为 None → 报告对应节显示"离线未采集"
    html_text = render_report(facts, args.url,
                              security_results=security_results,
                              sitemap_quality=sitemap_quality,
                              image_summary=image_summary,
                              not_found=not_found,
                              overall_score=overall_score if 'overall_score' in dir() else None,
                              psi_result=psi_result if 'psi_result' in dir() else None)
    report_path = out_dir / "audit-report.html"
    report_path.write_text(html_text, encoding="utf-8")
    print(f"[report] {report_path} ({report_path.stat().st_size} bytes)")
    print(f"[facts]  {data_dir / 'facts.json'}")
    print(f"         pages={len(facts['rows'])} "
          f"critical={facts['issues_count']['critical']} "
          f"major={facts['issues_count']['major']} "
          f"minor={facts['issues_count']['minor']}")
    return 0


def cmd_crawl(args) -> int:
    import subprocess
    script = Path(__file__).resolve().parent.parent / "scripts" / "crawl_docs.py"
    cmd = [sys.executable, str(script), "--source", args.source]
    if args.limit:
        cmd += ["--limit", str(args.limit)]
    return subprocess.call(cmd)


def cmd_geo_live(args) -> int:
    import os
    from .geo_live import run_geo_live, load_queries
    from urllib.parse import urlparse
    api_key = args.api_key or os.environ.get("GEO_LIVE_API_KEY", "")
    base_url = args.base_url or os.environ.get("GEO_LIVE_BASE_URL", "")
    model = args.model or os.environ.get("GEO_LIVE_MODEL", "")
    if not (api_key and base_url and model):
        print("缺少 LLM 配置：请设置 GEO_LIVE_API_KEY/GEO_LIVE_BASE_URL/GEO_LIVE_MODEL 或传参")
        return 2
    queries = load_queries(args.queries)
    host = urlparse(args.url).netloc
    brand_terms = [host.replace("www.", "")]
    out = run_geo_live(args.url, queries, brand_terms, api_key, base_url, model)
    print(f"mention_rate={out['mention_rate']} citation_rate={out['citation_rate']}")
    return 0


def cmd_push(args) -> int:
    import os
    from pathlib import Path
    from .site_push import push_indexnow, load_urls_from_facts
    key = args.key or os.environ.get("INDEXNOW_KEY", "")
    if not key:
        print("缺少 IndexNow key：--key 或 INDEXNOW_KEY")
        return 2
    facts = Path(args.out) / "data" / "facts.json" if args.out else Path("docs/site-audit/data/facts.json")
    urls = load_urls_from_facts(facts)
    print(push_indexnow(args.url, key, urls))
    return 0


def cmd_serve(args) -> int:
    from .web import serve
    serve(host=args.host, port=args.port, open_browser=not args.no_browser)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="geosentry",
                                description="GeoSentry — 本机 SEO/GEO 全站审计 + RAG 知识背板")
    p.add_argument("--data-dir", default=None, help="索引目录（默认项目 data/）")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("index", help="重建索引")
    sub.add_parser("info", help="索引状态")

    ps = sub.add_parser("search", help="检索")
    ps.add_argument("query", help="查询问题")
    ps.add_argument("--top-k", type=int, default=5)

    pa = sub.add_parser("audit", help="站点 GEO 审计（轻量单页 / --deep 全站逐页）")
    pa.add_argument("--url", required=True, help="目标站点 URL")
    pa.add_argument("--top-k", type=int, default=3)
    pa.add_argument("--no-verify-ssl", action="store_true",
                    help="不校验 SSL 证书（仅用于自签名/内网测试站点，默认校验）")
    pa.add_argument("--deep", action="store_true",
                    help="全站逐页深审：爬取 + 逐页分析 + 深色 HTML 报告")
    pa.add_argument("--out", default=None,
                    help="深审输出目录（默认 docs/site-audit-<host>）")
    pa.add_argument("--offline", default=None,
                    help="离线模式：直接分析本地 raw/ 目录的 HTML，不联网")
    pa.add_argument("--delay", type=float, default=None,
                    help="爬取限速秒数（默认 1.2）")
    pa.add_argument("--max-pages", type=int, default=None,
                    help="最多爬取 HTML 页数（调试用）")
    pa.add_argument("--bfs", action="store_true", default=False,
                    help="在线 --deep 模式下，除 sitemap 外再从首页 BFS 抓同域内链并合并去重")
    pa.add_argument("--bfs-fallback", dest="bfs_fallback", action="store_true",
                    default=True,
                    help="当 sitemap 解析结果为空时自动启用 BFS（默认开；用 --no-bfs-fallback 关）")
    pa.add_argument("--no-bfs-fallback", dest="bfs_fallback", action="store_false",
                    help="sitemap 为空时不自动启用 BFS")
    pa.add_argument("--external-probe", dest="external_probe", action="store_true",
                    default=False,
                    help="在线 --deep 模式下，死链探测也覆盖外链（限速 >=2s）")
    pa.add_argument("--concurrency", type=int, default=1, help="并发线程数（默认 1 保持礼貌）")
    pa.add_argument("--rate", type=float, default=None, help="token 桶次/秒（覆盖 --delay）")
    pa.add_argument("--cache", choices=["on","off","refresh"], default="on", help="磁盘缓存 on/off/refresh")
    pa.add_argument("--content-filter", choices=["pruning","bm25","none"], default="pruning", help="主内容提取模式")
    pa.add_argument("--ua", choices=["fixed","rotate"], default="fixed", help="UA 轮换（仅并发模式生效）")
    pa.add_argument("--render", choices=["off","auto","crawl4ai"], default="off", help="可选渲染层")
    pa.add_argument("--max-dead-probes", type=int, default=50,
                    help="死链探测上限（默认 50；0=不限制，注意会对目标站发大量请求）")

    pc = sub.add_parser("crawl", help="增量爬取语料")
    pc.add_argument("--source", default="google", choices=["google", "all"])
    pc.add_argument("--limit", type=int, default=None)

    gl = sub.add_parser("geo-live", help="GEO LLM 实测 mention/citation rate")
    gl.add_argument("--url", required=True, help="目标站点 URL")
    gl.add_argument("--queries", required=True, help="query 列表文件（每行一条）")
    gl.add_argument("--api-key", default=None, help="默认读 GEO_LIVE_API_KEY")
    gl.add_argument("--base-url", default=None, help="默认读 GEO_LIVE_BASE_URL")
    gl.add_argument("--model", default=None, help="默认读 GEO_LIVE_MODEL")

    pp = sub.add_parser("push", help="IndexNow 推送 URL")
    pp.add_argument("--url", required=True, help="目标站点 host")
    pp.add_argument("--key", default=None, help="IndexNow key（默认读 INDEXNOW_KEY）")
    pp.add_argument("--out", default=None, help="audit 输出目录（读其 data/facts.json）")

    sv = sub.add_parser("serve", help="启动本地 Web UI（浏览器填 URL 跑审计）")
    sv.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    sv.add_argument("--port", type=int, default=8765, help="端口（默认 8765）")
    sv.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")

    args = p.parse_args(argv)
    handlers = {"index": cmd_index, "search": cmd_search, "info": cmd_info,
                "audit": cmd_audit, "crawl": cmd_crawl,
                "geo-live": cmd_geo_live, "push": cmd_push, "serve": cmd_serve}
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
