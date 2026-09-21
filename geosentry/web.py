"""本地 Web 服务：浏览器填 URL，后台跑审计，实时进度 + 报告。

纯标准库 http.server，零依赖。
启动：py -3.11 -m geosentry serve [--port 8765] [--host 127.0.0.1]
"""
from __future__ import annotations

import json
import os
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

# job_id -> {status, progress, log, report_path, facts_path, error, geo}
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()

ROOT_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GeoSentry · AI-Powered SEO/GEO Auditor</title>
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  :root {
    --bg:#07090d;
    --bg2:#0d1117;
    --card:rgba(255,255,255,0.03);
    --card-border:rgba(255,255,255,0.08);
    --ink:#e6edf3;
    --dim:#7d8590;
    --accent:#7ee787;
    --accent2:#58a6ff;
    --warn:#f0b429;
    --bad:#ff6b6b;
    --grad: linear-gradient(135deg, #7ee787 0%, #58a6ff 100%);
  }
  html,body { height:100%; }
  body {
    background: var(--bg);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
    line-height:1.5;
    overflow-x:hidden;
  }
  /* 背景光晕 */
  body::before {
    content:""; position:fixed; top:-200px; left:50%; transform:translateX(-50%);
    width:900px; height:600px;
    background: radial-gradient(circle, rgba(126,231,135,0.12) 0%, transparent 60%),
                radial-gradient(circle at 70% 50%, rgba(88,166,255,0.10) 0%, transparent 60%);
    pointer-events:none; z-index:0;
  }
  .wrap { position:relative; z-index:1; max-width:960px; margin:0 auto; padding:60px 24px 80px; }

  /* Hero */
  .hero { text-align:center; margin-bottom:48px; }
  .logo {
    display:inline-flex; align-items:center; gap:10px;
    padding:6px 16px; border-radius:999px;
    background:rgba(126,231,135,0.08); border:1px solid rgba(126,231,135,0.25);
    font-size:13px; color:var(--accent); margin-bottom:24px;
    font-weight:500; letter-spacing:0.5px;
  }
  .logo .dot { width:8px; height:8px; border-radius:50%; background:var(--accent);
               box-shadow:0 0 12px var(--accent); animation:pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  h1 {
    font-size: clamp(36px, 6vw, 56px); font-weight:800; letter-spacing:-1.5px;
    background: var(--grad); -webkit-background-clip:text; background-clip:text;
    -webkit-text-fill-color:transparent; margin-bottom:16px; line-height:1.1;
  }
  .sub { color:var(--dim); font-size:17px; max-width:560px; margin:0 auto; }

  /* 卡片 */
  .card {
    background: var(--card); border:1px solid var(--card-border);
    border-radius:20px; padding:32px;
    backdrop-filter: blur(20px);
    margin-bottom:24px;
  }

  /* 表单 */
  .url-row { display:flex; gap:12px; margin-bottom:20px; }
  input[type=url], input[type=text], input[type=number], input[type=password], textarea, select {
    flex:1; padding:16px 18px; border-radius:12px;
    border:1px solid var(--card-border); background:rgba(0,0,0,0.3);
    color:var(--ink); font-size:15px; font-family:inherit;
    transition: border-color .2s, box-shadow .2s;
  }
  input:focus, textarea:focus, select:focus {
    outline:none; border-color:var(--accent);
    box-shadow:0 0 0 3px rgba(126,231,135,0.15);
  }
  input::placeholder { color:var(--dim); }
  button.go {
    padding:16px 32px; border-radius:12px; border:0;
    background: var(--grad); color:#0a0e14; font-weight:700; font-size:15px;
    cursor:pointer; transition: transform .15s, box-shadow .15s;
    white-space:nowrap;
  }
  button.go:hover { transform:translateY(-1px); box-shadow:0 8px 24px rgba(126,231,135,0.3); }
  button.go:disabled { opacity:0.5; cursor:not-allowed; transform:none; }

  .opts { display:flex; gap:20px; flex-wrap:wrap; color:var(--dim); font-size:14px; }
  .opts label { display:flex; align-items:center; gap:8px; cursor:pointer; }
  .opts input[type=checkbox] { accent-color:var(--accent); width:16px; height:16px; }
  .opts input[type=number] { width:70px; padding:6px 8px; }

  /* 高级选项折叠 */
  .adv-toggle {
    width:100%; text-align:left; background:none; border:0; color:var(--dim);
    padding:16px 0; cursor:pointer; font-size:14px; display:flex; justify-content:space-between;
    align-items:center; border-top:1px solid var(--card-border); margin-top:8px;
  }
  .adv-toggle:hover { color:var(--ink); }
  .adv-body { display:none; padding-top:16px; }
  .adv-body.open { display:block; }
  .field { margin-bottom:14px; }
  .field label { display:block; font-size:13px; color:var(--dim); margin-bottom:6px; }
  .field input, .field textarea { width:100%; }
  .field-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; }

  /* 进度区 */
  #status { display:none; margin-top:24px; }
  .progress-wrap {
    background:var(--card); border:1px solid var(--card-border);
    border-radius:14px; padding:20px 24px; margin-bottom:16px;
  }
  .progress-top { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:10px; }
  .progress-stage { font-size:13px; color:var(--dim); }
  .progress-pct { font-size:28px; font-weight:800; font-family:"SF Mono",monospace; color:var(--accent); }
  .progress-bar {
    height:8px; background:rgba(255,255,255,0.06); border-radius:99px; overflow:hidden;
    position:relative;
  }
  .progress-fill {
    height:100%; background:var(--grad); border-radius:99px;
    transition: width .4s ease; width:0%;
  }
  .progress-detail {
    margin-top:10px; font-size:12.5px; color:var(--dim);
    font-family:"SF Mono",monospace; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }
  .log {
    background:rgba(0,0,0,0.4); border:1px solid var(--card-border);
    border-radius:12px; padding:18px; height:220px; overflow-y:auto;
    font-family:"SF Mono", ui-monospace, monospace; font-size:12.5px;
    color:var(--dim); white-space:pre-wrap; line-height:1.6;
    scrollbar-width: thin;
    scrollbar-color: rgba(126,231,135,0.3) transparent;
  }
  .log::-webkit-scrollbar { width:8px; }
  .log::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); border-radius:99px; }
  .log::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, rgba(126,231,135,0.4), rgba(88,166,255,0.4));
    border-radius:99px;
  }
  .log::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, rgba(126,231,135,0.7), rgba(88,166,255,0.7));
  }
  .log .ok { color:var(--accent); }
  .log .warn { color:var(--warn); }
  .log .err { color:var(--bad); }

  /* 分数卡片 */
  .score-grid {
    display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr));
    gap:14px; margin-top:20px;
  }
  .score-cell {
    background:var(--card); border:1px solid var(--card-border);
    border-radius:14px; padding:20px; text-align:center;
  }
  .score-cell .num {
    font-size:36px; font-weight:800; font-family:"SF Mono", monospace;
    letter-spacing:-1px;
  }
  .score-cell .lab { font-size:12px; color:var(--dim); margin-top:6px; text-transform:uppercase; letter-spacing:1px; }
  .g-A { color:var(--accent); } .g-B { color:var(--accent2); }
  .g-C { color:var(--warn); } .g-D,.g-F { color:var(--bad); }

  /* 报告 */
  #report { display:none; margin-top:24px; }
  #report iframe {
    width:100%; height:760px; border:1px solid var(--card-border);
    border-radius:14px; background:#fff;
  }
  .report-bar {
    display:flex; justify-content:space-between; align-items:center;
    margin-bottom:12px; padding:0 4px;
  }
  .report-bar a { color:var(--accent); text-decoration:none; font-size:14px; }
  .report-bar a:hover { text-decoration:underline; }

  /* 动画 */
  .fade-in { animation: fadeIn .4s ease; }
  @keyframes fadeIn { from{opacity:0; transform:translateY(8px)} to{opacity:1; transform:none} }
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="logo"><span class="dot"></span> GeoSentry · Local-First</div>
    <h1>Audit Your Site.<br>Know Why AI Ignores It.</h1>
    <p class="sub">本机运行 · 数据不上传 · 全站逐页扫描 · SEO/GEO 双维度评分</p>
  </div>

  <div class="card">
    <form id="f">
      <div class="url-row">
        <input type="url" name="url" required placeholder="https://your-site.com" autofocus>
        <button type="submit" class="go" id="go">开始审计 →</button>
      </div>
      <div class="opts">
        <label><input type="checkbox" name="deep" checked> 全站深审</label>
        <label>并发 <input type="number" name="concurrency" value="2" min="1" max="8"></label>
        <label><input type="checkbox" name="cache" checked> 磁盘缓存</label>
        <label>死链上限 <input type="number" name="max_dead_probes" value="50" min="0" style="width:80px"></label>
      </div>
      <div class="field" style="margin-top:14px">
        <label style="font-size:13px;color:var(--dim)">HTTP 代理（可选 · 国内访问 Google PSI 用，如 http://127.0.0.1:7890）</label>
        <input type="text" name="proxy" placeholder="http://127.0.0.1:7890" style="margin-top:6px">
      </div>

    </form>
  </div>

  <div id="status">
    <div class="progress-wrap">
      <div class="progress-top">
        <span class="progress-stage" id="stageLabel">准备中…</span>
        <span class="progress-pct" id="pctLabel">0%</span>
      </div>
      <div class="progress-bar"><div class="progress-fill" id="bar"></div></div>
      <div class="progress-detail" id="detailLabel"></div>
    </div>
    <div class="log" id="log"></div>
    <div class="score-grid" id="score"></div>
  </div>

  <div id="report">
    <div class="report-bar">
      <span style="color:var(--dim);font-size:13px">完整报告</span>
      <span style="display:flex;gap:16px;align-items:center">
        <button type="button" id="fsBtn" style="background:none;border:1px solid var(--card-border);color:var(--dim);padding:6px 12px;border-radius:8px;cursor:pointer;font-size:13px">全屏</button>
        <a id="openNew" target="_blank">在新窗口打开 ↗</a>
      </span>
    </div>
    <iframe id="frame" src="about:blank" style="height:85vh"></iframe>
  </div>
</div>

<script>
const f = document.getElementById('f'), log = document.getElementById('log');
const go = document.getElementById('go'), status = document.getElementById('status');
const score = document.getElementById('score'), rep = document.getElementById('report');
const bar = document.getElementById('bar'), pctLabel = document.getElementById('pctLabel');
const stageLabel = document.getElementById('stageLabel'), detailLabel = document.getElementById('detailLabel');

function updateProgress(p) {
  if (!p) return;
  const total = p.total || 0, cur = p.current || 0;
  let pct = 0;
  if (p.stage === '1/3') {
    pct = 8; stageLabel.textContent = '① 解析 sitemap / robots';
  } else if (p.stage === '2/3' && total) {
    pct = 10 + (cur/total) * 70;
    stageLabel.textContent = `② 爬取页面 ${cur}/${total}`;
  } else if (p.stage === '3/3' && total) {
    pct = 80 + (cur/total) * 15;
    stageLabel.textContent = `③ 探测 PDF ${cur}/${total}`;
  } else {
    stageLabel.textContent = p.stage === 'crawl' ? '② 爬取中' : '准备中…';
  }
  bar.style.width = Math.min(100, pct) + '%';
  pctLabel.textContent = Math.round(pct) + '%';
  if (p.detail) detailLabel.textContent = p.detail;
}

document.getElementById('fsBtn').onclick = () => {
  const f = document.getElementById('frame');
  if (f.requestFullscreen) f.requestFullscreen();
};

f.addEventListener('submit', async (e) => {
  e.preventDefault();
  go.disabled = true; log.textContent = '';
  status.style.display = 'block'; rep.style.display = 'none'; score.innerHTML = '';
  const body = new URLSearchParams(new FormData(f));
  const r = await fetch('/audit', { method:'POST', body });
  const j = await r.json();
  poll(j.job_id);
});

async function poll(id) {
  const r = await fetch('/status/' + id);
  const j = await r.json();
  if (j.log) { log.textContent = j.log; log.scrollTop = log.scrollHeight; }
  updateProgress(j.progress);
  if (j.status === 'running') { setTimeout(() => poll(id), 1000); return; }
  bar.style.width = '100%'; pctLabel.textContent = '100%';
  stageLabel.textContent = '完成';
  go.disabled = false;
  if (j.status === 'error') {
    score.innerHTML = '<div class="score-cell"><div class="num g-F">失败</div><div class="lab">'+(j.error||'')+'</div></div>';
    return;
  }
  let html = '';
  if (j.score) {
    const s = j.score;
    html += `<div class="score-cell fade-in"><div class="num g-${s.grade}">${s.pct}</div><div class="lab">总分 · ${s.grade}</div></div>`;
  }
  html += `<div class="score-cell fade-in"><div class="num g-C">${j.critical||0}</div><div class="lab">Critical</div></div>`;
  html += `<div class="score-cell fade-in"><div class="num g-C">${j.major||0}</div><div class="lab">Major</div></div>`;
  html += `<div class="score-cell fade-in"><div class="num">${j.minor||0}</div><div class="lab">Minor</div></div>`;
  if (j.geo && j.geo.mention_rate != null) {
    html += `<div class="score-cell fade-in"><div class="num g-B">${(j.geo.mention_rate*100).toFixed(0)}%</div><div class="lab">LLM 提及率</div></div>`;
    html += `<div class="score-cell fade-in"><div class="num g-B">${(j.geo.citation_rate*100).toFixed(0)}%</div><div class="lab">LLM 引用率</div></div>`;
  }
  score.innerHTML = html;
  document.getElementById('frame').src = '/report/' + id;
  document.getElementById('openNew').href = '/report/' + id;
  rep.style.display = 'block';
}
</script>
</body>
</html>"""


def _run_job(job_id: str, url: str, deep: bool, concurrency: int, use_cache: bool,
             geo_cfg: dict):
    """后台线程：跑 audit + 可选 GEO LLM 实测，把日志/结果写进 JOBS。"""
    import sys
    from pathlib import Path

    out_dir = Path.cwd() / "docs" / f"web-audit-{uuid.uuid4().hex[:8]}"

    # 实时同步 stdout 到 JOBS：每次 print 都立即更新前端能看到的 log
    # 同时从日志里解析 [N/M] 格式进度，更新 progress
    import re
    _prog_re = re.compile(r'\[\s*(\d+)/(\d+)\]\s*(.*)')
    _stage_re = re.compile(r'\[(\d/3)\]\s*(.*)')

    class _LiveLog:
        def __init__(self):
            self.buf = ""
            self.progress = {"current": 0, "total": 0, "stage": "init", "detail": "启动中"}
        def write(self, s):
            if not s: return 0
            self.buf += s
            for line in s.splitlines():
                m = _prog_re.search(line)
                if m:
                    cur, tot = int(m.group(1)), int(m.group(2))
                    self.progress = {
                        "current": cur, "total": tot,
                        "stage": self.progress["stage"],
                        "detail": m.group(3).strip()[:120],
                    }
                sm = _stage_re.search(line)
                if sm:
                    self.progress["stage"] = sm.group(1)
                    self.progress["detail"] = sm.group(2).strip()[:120]
                low = line.lower()
                if 'crawling' in low or 'fetching' in low or 'probing' in low:
                    self.progress["detail"] = line.strip()[:120]
            with JOBS_LOCK:
                JOBS[job_id]["log"] = self.buf
                JOBS[job_id]["progress"] = self.progress
            return len(s)
        def flush(self): pass
        def isatty(self): return False

    live = _LiveLog()
    old_stdout = sys.stdout
    sys.stdout = live
    # 代理配置：让 urllib 走代理访问 Google PSI
    proxy = geo_cfg.get("proxy", "")
    if proxy:
        os.environ["HTTP_PROXY"] = proxy
        os.environ["HTTPS_PROXY"] = proxy
        print(f"[proxy] using {proxy}")
    try:
        from .cli import _cmd_audit_deep

        class A: pass
        args = A()
        args.url = url
        args.deep = True
        args.out = str(out_dir)
        args.offline = None
        args.delay = None
        args.max_pages = None
        args.bfs = False
        args.bfs_fallback = True
        args.no_bfs_fallback = False
        args.external_probe = False
        args.concurrency = concurrency
        args.rate = None
        args.cache = "on" if use_cache else "off"
        args.content_filter = "pruning"
        args.ua = "fixed"
        args.render = "off"
        args.no_verify_ssl = False
        args.top_k = 3
        args.max_dead_probes = geo_cfg.get("max_dead_probes", 50)

        _cmd_audit_deep(args)

        facts = json.loads((out_dir / "data" / "facts.json").read_text(encoding="utf-8"))
        report_path = out_dir / "audit-report.html"

        # 可选：GEO LLM 实测
        geo_result = None
        if geo_cfg.get("enabled"):
            try:
                from .geo_live import run_geo_live, load_queries
                from urllib.parse import urlparse
                queries_file = out_dir / "queries.txt"
                queries_file.write_text(geo_cfg["queries"], encoding="utf-8")
                host = urlparse(url).netloc
                brand = [host.replace("www.", "")]
                geo_result = run_geo_live(
                    url, load_queries(str(queries_file)), brand,
                    geo_cfg["key"], geo_cfg["base"], geo_cfg["model"])
            except Exception as e:
                with JOBS_LOCK:
                    JOBS[job_id]["log"] = live.buf + f"\n[geo] skipped: {e}\n"

        with JOBS_LOCK:
            JOBS[job_id].update({
                "status": "done",
                "log": live.buf,
                "report_path": str(report_path),
                "issues": facts.get("issues_count", {}),
                "geo": geo_result,
            })
    except Exception as e:
        import traceback
        with JOBS_LOCK:
            JOBS[job_id].update({
                "status": "error",
                "error": f"{type(e).__name__}: {e}",
                "log": live.buf + "\n" + traceback.format_exc(),
            })
    finally:
        sys.stdout = old_stdout


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, ROOT_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path.startswith("/status/"):
            jid = self.path.split("/status/", 1)[1]
            with JOBS_LOCK:
                j = JOBS.get(jid, {})
                issues = j.get("issues", {})
                geo = j.get("geo") or {}
                body = json.dumps({
                    "status": j.get("status", "unknown"),
                    "log": j.get("log", ""),
                    "error": j.get("error"),
                    "critical": issues.get("critical", 0),
                    "major": issues.get("major", 0),
                    "minor": issues.get("minor", 0),
                    "score": None,
                    "progress": j.get("progress"),
                    "geo": {
                        "mention_rate": geo.get("mention_rate"),
                        "citation_rate": geo.get("citation_rate"),
                    } if geo else None,
                }).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        elif self.path.startswith("/report/"):
            jid = self.path.split("/report/", 1)[1]
            with JOBS_LOCK:
                rp = JOBS.get(jid, {}).get("report_path")
            if rp and Path(rp).exists():
                self._send(200, Path(rp).read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, b"not found", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != "/audit":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        q = parse_qs(body, keep_blank_values=True)
        url = q.get("url", [""])[0].strip()
        deep = "deep" in q
        concurrency = int(q.get("concurrency", ["2"])[0])
        use_cache = "cache" in q

        geo_cfg = {
            "enabled": "geo_live" in q,
            "key": q.get("llm_key", [""])[0].strip(),
            "base": q.get("llm_base", [""])[0].strip(),
            "model": q.get("llm_model", [""])[0].strip(),
            "queries": q.get("queries", [""])[0].strip(),
            "max_dead_probes": int(q.get("max_dead_probes", ["50"])[0] or 50),
            "proxy": q.get("proxy", [""])[0].strip(),
        }
        if geo_cfg["enabled"]:
            if not (geo_cfg["key"] and geo_cfg["base"] and geo_cfg["model"] and geo_cfg["queries"]):
                self._send(400, json.dumps({"error": "GEO 实测需要完整的 key/base/model/queries"}).encode(),
                           "application/json; charset=utf-8")
                return

        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        jid = uuid.uuid4().hex[:12]
        with JOBS_LOCK:
            JOBS[jid] = {"status": "running", "log": ""}
        t = threading.Thread(target=_run_job,
                             args=(jid, url, deep, concurrency, use_cache, geo_cfg),
                             daemon=True)
        t.start()
        self._send(200, json.dumps({"job_id": jid}).encode("utf-8"), "application/json")


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True):
    srv = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"GeoSentry web UI: {url}")
    print(f"按 Ctrl+C 停止")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
