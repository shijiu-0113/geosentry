# GeoSentry — Agent Integration Manual

> This document is for AI agents / LLMs that need to drive GeoSentry as a CLI tool.
> Humans: see README.md. Agents: read this.

---

## 1. What it does

GeoSentry is a **local-first SEO/GEO site auditor**. It crawls a target site page-by-page,
runs ~40 technical checks per page, and outputs:

- An HTML report (dark theme, self-contained, printable)
- A JSON facts file (machine-readable)
- A numeric score (A–F) with critical / major / minor issue counts

**No external API keys required** for the core audit. Optional: Google PageSpeed Insights
(no key needed, rate-limited), GEO LLM live test (needs OpenAI-compatible key).

---

## 2. Environment

- Python **3.11+** required (uses `match` / `X | Y` type unions)
- **Pure stdlib** — zero pip dependencies for the core audit
- Cross-platform: Windows / macOS / Linux
- On minimal Linux images, run `apt install ca-certificates` first to avoid SSL errors

---

## 3. Invocation

Always `cd` into the project root (the folder containing `geosentry/`) first.

### 3.1 Web UI (recommended for humans)

```bash
python3 -m geosentry serve --host 127.0.0.1 --port 8765
# then open http://127.0.0.1:8765 in a browser
# add --host 0.0.0.0 if accessing from another machine
```

### 3.2 CLI deep audit (recommended for agents)

```bash
python3 -m geosentry audit \
  --url https://example.com \
  --deep \
  --out ./docs/site-audit-example \
  --concurrency 2 \
  --max-dead-probes 50
```

**Parameters:**

| Param | Type | Default | Meaning |
|---|---|---|---|
| `--url` | str | required | Target site root URL |
| `--deep` | flag | off | Enable full-site crawl (without this, single-page only) |
| `--out` | path | `docs/site-audit` | Output directory |
| `--concurrency` | int | 1 | Parallel fetch threads (2 is polite) |
| `--max-dead-probes` | int | 50 | Cap on dead-link probes; `0` = unlimited |
| `--delay` | float | 1.2 | Seconds between requests (politeness) |
| `--no-verify-ssl` | flag | off | Skip TLS verification (for self-signed certs / minimal images) |
| `--external-probe` | flag | off | Also probe outbound links |
| `--cache` | enum | `on` | `on` / `off` / `refresh` |
| `--max-pages` | int | none | Hard cap on pages (debugging) |
| `--offline <dir>` | path | none | Analyze local HTML files instead of crawling |

### 3.3 Exit codes

| Code | Meaning |
|---|---|
| 0 | Audit completed (even if score is low) |
| 1 | Not indexed (search subcommand only) |
| 2 | Bad arguments / missing required field |

---

## 4. Output contract

After a successful run, `--out` contains:

```
docs/site-audit-example/
├── audit-report.html   ← self-contained HTML, open in browser
├── data/
│   ├── facts.json      ← machine-readable, parse this
│   └── pages.json      ← raw per-page crawl data
└── raw/                ← saved HTML pages (for re-analysis)
```

### 4.1 facts.json schema

```json
{
  "site": "https://example.com",
  "counts": { "html": 73, "pdf": 34 },
  "rows": [
    {
      "url": "https://example.com/about",
      "title": "About Us",
      "h1": "...",
      "issues": [
        { "severity": "major", "code": "MISSING_META_DESC", "message": "..." }
      ]
    }
  ],
  "issues_count": { "critical": 0, "major": 8, "minor": 9 },
  "overall": { "pct": 56.8, "grade": "D" }
}
```

### 4.2 Severity levels

| Level | Weight | Action |
|---|---|---|
| `critical` | 10 | Fix immediately — actively hurts indexing |
| `major` | 5 | Clear gap, measurable impact |
| `minor` | 2 | Polish |

### 4.3 Grade bands

| Grade | Score |
|---|---|
| A | 90–100 |
| B | 75–89 |
| C | 60–74 |
| D | 40–59 |
| F | <40 |

---

## 5. What the audit checks (~40 items)

**Per-page (HTML):**
- `<title>` present, length 30–60 chars
- `<meta name="description">` present, length 120–160
- Exactly one `<h1>`
- Canonical URL present and self-referential
- Open Graph / Twitter Card tags
- `viewport` meta
- HTML `lang` attribute
- JSON-LD structured data parseable
- Internal / external link coverage
- Image `alt` text coverage
- Word count (thin content < 300 words)

**Cross-page:**
- Duplicate titles / meta descriptions
- Orphan pages (no internal links pointing to them)
- Dead internal links (HTTP 4xx)
- Soft 404 detection
- Sitemap XML validity
- robots.txt AI-crawler per-UA report (GPTBot, ClaudeBot, PerplexityBot, Google-Extended)
- llms.txt presence + structure

**Site-wide:**
- HTTPS valid cert
- Security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, COOP/COEP/CORP
- Image format (WebP/AVIF), lazy loading, width/height attrs
- 404 page content
- PageSpeed Insights (optional, via Google API; 6s timeout, auto-skip if unreachable)

---

## 6. Agent workflow recipe

When asked to "audit a site":

1. **Pick a unique output dir** so runs don't collide:
   `--out ./docs/site-audit-$(host)-$(timestamp)`
2. **Run the CLI** (not the web UI — agents should use CLI):
   ```bash
   python3 -m geosentry audit --url <url> --deep --out <dir> --concurrency 2
   ```
3. **Wait for exit code 0**. Progress prints to stdout as `[N/M]` lines.
4. **Parse `data/facts.json`** — don't parse the HTML report.
5. **Summarize for the user:**
   - Overall score + grade
   - Top critical / major issues (by frequency across pages)
   - One sentence on what to fix first
6. **Attach `audit-report.html`** as the deliverable.

### Timeouts

- Small site (< 50 pages): ~30 seconds
- Medium (100–300 pages): 2–5 minutes
- Large (1000+ pages): 10+ minutes
- PSI step adds up to 6 seconds (auto-skips if blocked)

---

## 7. Common errors and fixes

| Error | Cause | Fix |
|---|---|---|
| `[SSL: CERTIFICATE_VERIFY_FAILED]` | Server lacks CA certs | `apt install ca-certificates`, or add `--no-verify-ssl` |
| `SyntaxError` on start | Python < 3.11 | Upgrade to Python 3.11+ |
| `Address already in use` | Port taken | `--port 8766` |
| All pages show empty title / H1 | `content_filter` bug on specific HTML | Report it; try `--content-filter none` |
| PSI skipped / 429 | Google rate limit | Normal; skip, doesn't affect other checks |
| `ModuleNotFoundError: geosentry` | Wrong working directory | `cd` to project root first |

---

## 8. Non-goals (don't ask for these)

- No JS rendering / headless browser (static HTML only)
- No real-user PageSpeed data (only lab PSI if reachable)
- No Google Search Console integration
- No backlink analysis
- No multi-language hreflang validation (basic check only)
- The GEO LLM live test module exists but is not exposed in the web UI; use `geo-live` subcommand if needed
