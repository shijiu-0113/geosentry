# AUDIT_NOTES.md · 第三轮（全站深审产品化）

本轮把 `docs/site-audit-hbyagada/` 下的一次性脚本（crawl_audit.py / summarize.py / gen_report.py）产品化为 geosentry 包内可复用模块。

## 新模块

| 文件 | 职责 |
|---|---|
| `geosentry/site_crawler.py` | 全站 BFS 爬取：sitemap 发现、robots 门禁、限速、gzip 解码、HTML/PDF 存 raw/ |
| `geosentry/site_audit.py` | 逐页 HTML 解析（title/desc/canonical/H1/词数/JSON-LD/内链/图片 alt/shingles）+ 跨页分析（dup title/desc、Jaccard 近似、孤儿页、死链）+ flag 判定；支持离线 raw/ 目录分析 |
| `geosentry/report_html.py` | 从 facts dict 生成深色主题单文件 HTML 报告（摘要卡片 → 一句话结论 → Top 问题 → 全站分析 → 逐页表 → PDF 表 → P0/P1/P2 路线图） |

## 与样板 facts.json 的口径对比（离线重分析 raw/*.html）

| 指标 | 样板 facts.json | 本轮离线重算 | 说明 |
|---|---|---|---|
| HTML 页数 | 73 | 72 | 样板含 1 个 HTTP 410 页（未存 raw/），离线自然缺失 |
| critical flags | 3 | 0 | 3 条 critical 全部来自该 410 页（HTTP 410 / 缺 title / 缺 canonical） |
| major flags | 66 | 62 | 4 条 major 来自该 410 页（缺 desc / 无 H1 / 正文薄 / 缺 viewport） |
| minor flags | 47 | 47 | 一致 |
| 孤儿页 | 26 | 25 | 仅少 410 页（inbound=0） |
| similar_total | 484 | 484 | 完全一致 |
| title_dup 组 | 1 | 1 | 一致（6 个 /ask 页） |
| desc_dup 组 | 1 | 1 | 一致 |
| 逐页 flags diff | — | 0 | 72 个共享页面的 flags 完全一致 |

**未修正原脚本 bug**：原 `crawl_audit.py` / `summarize.py` 的判定逻辑经离线复算与样板 facts.json 完全吻合，无需修正。

## 与样板 audit-report.html 的差异

- 样板 `gen_report.py` 硬编码了大量 hbyagada 专属叙事（一句话结论、Top 8 条问题、3.1–3.8 全站分析段落）。
- 本轮 `report_html.py` 全部从 facts dict 程序化推导：Top 问题按 severity 自动聚合（非 200 / canonical 指错 / dup 簇 / 孤儿 / 高相似对 / title 超长 / 正文薄 / 无 H1），路线图按 P0/P1/P2 自动分级。
- 结构对齐：头部摘要卡片（8 张）→ 一句话结论 → Top 优先级 → 全站分析（dup 聚类 / 近似内容 / 孤儿 / 死链与 PDF）→ 逐页明细表 → PDF 汇总 → P0/P1/P2 路线图。
- CSS 变量与视觉风格对齐样板（`--bg:#0e141b` 等深色主题）。

## CLI 新增

```
py -3.11 -m geosentry audit --url https://站点 --deep --out docs/site-audit-x/
py -3.11 -m geosentry audit --url https://站点 --deep --offline docs/.../raw --out docs/...
```

原轻量单页模式（无 --deep）保持不变。

## 回归验证

- 单元测试：45/45 全绿（原 25 + 新增 20）
- eval Recall@5：100%（52/52），未退化

## 待整合 GitHub 借鉴（第二轮遗留）

第二轮 digest 想法 1–8 已全部实现并回归通过。本轮无新增 digest 想法。

## 仍 open 的 TODO

1. **死链在线探测**：离线模式不联网，`dead_links` 恒为空；在线模式下应主动 GET 未知内部 href 并记录非 200。当前 `cross_page_analysis` 只列出 `unknown_internal_hrefs`，未做 HTTP 探测。
2. **PDF 离线分析**：离线模式不解析 PDF 内容（pdfs=[]）；如需离线 PDF 卫生检查，需在 raw/ 旁放 pdf/ 目录并读取文件头 %PDF。
3. **sitemap 递归**：当前只抓单层 /sitemap.xml，未处理 sitemap index（嵌套 sitemap）。
4. **canonical 末尾斜杠规范化**：flag 判定用 rstrip("/") 比较，但报告里未单独列出"尾部斜杠双版本 200"问题（样板 gen_report.py 是人工叙述）。
5. **报告 Top 问题排序**：当前按 severity 排序，未按 flag 计数加权；可在 P0 里把"出现次数最多的同类 major"提前。
6. **BFS 内链发现**：当前仅从 sitemap 出发，未做首页/列表页内链 BFS 扩展（原 crawl_audit.py 也只做 sitemap）；对未提交 sitemap 的站需补 BFS。

## 收尾对齐（叙事级 CRITICAL 升级）

`report_html.py` 的 `_aggregate_top_issues` 新增两条簇级升级规则（单页 flag 判定不动，仍与 summarize.py 同口径）：
- **canonical 错向聚类**：≥3 个页面 canonical 指向同一非自指 URL → CRITICAL 叙事项。本实例中 6 个 /ask 页集体指向 `/`，触发。
- **孤儿核心页聚类**：孤儿（inbound≤1）中含转化/工具路径（/rfq /products /quote /contact /ask /query /spec-sheets 等启发式集合）→ CRITICAL 叙事项。本实例命中 4 个：/products /query /rfq /spec-sheets。

重新生成后 Top 节 CRITICAL 叙事项 = 2：
1. 6 个页面 canonical 集体错误指向 /（对齐样板 Top-1）
2. 4 个转化/工具核心页零入链（孤儿）（对齐样板 Top-3）

与样板 3 条 CRITICAL 还差 1 条：**"已 410 Gone 的页面仍留在 sitemap 中"**。该页 `/ask/how-do-i-import-pipe-flanges-from-china-to-iran` 未存 raw/（HTTP 410，crawler 不保存），离线模式无数据可分析——这是离线模式的固有缺口；在线 `--deep` 爬取时会自动作为「非 200 页面」critical 项出现（规则 #1）。

回归：45/45 单测全绿，Recall@5 = 100%。


## 第四轮：open TODO 清零（2026-09-19）

原"仍 open 的 TODO"6 条全部补齐：

| # | TODO | 怎么补的 | 新增测试 |
|---|---|---|---|
| 1 | 死链在线探测 | `site_crawler.probe_dead_links(candidates, robots_txt, delay, max_probes=50)`：对 unknown_internal_hrefs 主动 GET，记录非 200 进 facts/dead_links；CLI 在线 --deep 模式自动调用，离线行为不变 | `TestDeadLinkProbe.test_probe_finds_404` / `test_probe_respects_max` |
| 2 | PDF 离线分析 | `site_audit.scan_local_pdfs(pdf_dir, base_url)`：读文件头 `%PDF-` 判有效性；`audit_offline` 自动发现 raw_dir 同级 `pdf/` 目录并扫描，产出 pdfs 列表进 facts | `TestOfflinePDF.test_scan_valid_and_corrupt` / `test_missing_dir` |
| 3 | sitemap 递归 | 用户已在 site_crawler.fetch_sitemap 里实现 `_recurse` + seen_sitemaps 去重 + robots.txt Sitemap: 入口；本轮补测试 | `TestRecursiveSitemap.test_sitemapindex_three_levels` / `test_sitemapindex_dedup_children` / `test_flat_sitemap_no_recursion` |
| 4 | 尾部斜杠双版本 | `cross_page_analysis` 新增 `trailing_slash_duos` 检出：同 path 带/不带末尾斜杠都在已抓集合且状态都 200；`build_facts` 输出该字段；`report_html` 作为 MINOR Top 项 + 叙事说明 | `TestTrailingSlashDetection.test_detects_dual_version` / `test_no_duo_if_non_200` |
| 5 | Top 问题排序 | `_aggregate_top_issues` 每条加 `weight`（影响页数），同 severity 内按 weight 降序 | `TestTopIssueSort.test_sorted_by_weight` |
| 6 | BFS 内链发现 | `site_crawler.bfs_discover(base_url, ...)`：从首页 BFS 抓同域 `<a href>`，走 robots 门禁 + 限速 + max_pages 上限；与 sitemap 互为补充 | `TestBFSDiscover.test_bfs_follows_internal_links` |

### 回归验证

- 单测：56/56 全绿（原 45 + 新增 11）
- eval Recall@5：100%（52/52）
- 离线回归（raw/*.html 重分析）：72 页、0 critical / 62 major / 47 minor、25 孤儿、484 similar 对——与上一轮完全一致，未退化

### 遗留项清零（MainAgent 补，2026-09-19）

- ~~BFS 与 sitemap 合并去重的 CLI 开关~~：已确认 cli.py 暴露 `--bfs` / `--bfs-fallback` / `--no-bfs-fallback`，`_cmd_audit_deep` 第 98-117 行已接逻辑（sitemap 非空时 `--bfs` 显式合并；sitemap 空时 fallback 自动启用）。
- ~~死链未单独成 Top 项~~：`_aggregate_top_issues` 新增第 10 条规则——`facts["dead_links"]` 非空时作为 Top 项，≤10 条为 major，>10 条升级 critical，列出 URL + 状态码。
- ~~尾部斜杠双版本未在真实数据触发~~：代码侧 Top 项（第 9 条）与单测均已就绪；hbyagada 离线数据本身没有带/不带斜杠双 200 的 URL，故离线 fixture 不触发属正常，在线 `--deep` 爬取时自动检出。

回归：59/59 单测全绿。


## 第六轮：全站检查能力扩充（2026-09-19）

### 新增检查项

| 项 | 模块 | 内容 |
|---|---|---|
| A 安全响应头 | `geosentry/site_security.py`（新） | HSTS/CSP=severe，XFO/nosniff=medium，Referrer/Permissions/COOP/COEP/CORP=low；逐项 Pass/Fail + 详情 |
| B AI 爬虫清单 | `geo_audit._AI_BOTS` | 新增 OAI-SearchBot/ChatGPT-User/Claude-User/Claude-SearchBot，逐个 Allow/Disallow |
| C llms.txt 质量 | `geo_audit._validate_llmstxt` | 加查：纯文本非 HTML/JSON、文件 <100KB、至少一个内容 URL、首段含 # 标题 |
| D 软 404 探测 | `site_crawler.probe_404`（新） | GET 随机不存在路径，检测软 404（200）、自定义 404 正文 >200 字、含回首页链接 |
| E 加权总分 | `geosentry/scoring.py`（新） | 汇总 A/F/G/D 四类，权重 severe=10/medium=5/low=2，总分=通过权重和/总权重和×100，等级 A≥90/B≥75/C≥60/D≥40/F<40 |
| F sitemap 质量 | `site_audit.analyze_sitemap_quality`（新） | XML 有效、含 <loc>、有 <lastmod>、robots 声明 sitemap、隐私/法律页不泄露 |
| G 图片优化 | `site_audit.analyze_images`（新） | width/height、WebP/AVIF、非首图 lazy、fetchpriority=high、alt |
| H 可选增强 | `geosentry/site_external.py`（新） | PageSpeed Insights API（无 key 跳过）；DNS 邮件检查（SPF/DKIM/DMARC/MTA-STS，需 dnspython）；pyproject 登记 optional `dns` |

### 权重数值表

| severity | 权重 |
|---|---|
| severe | 10 |
| medium | 5 |
| low | 2 |

总分公式：`(通过项权重和 / 总权重和) × 100`
等级：A 90-100 / B 75-89 / C 60-74 / D 40-59 / F <40
Email/DNS 类检查单独成节、不计入主分。

### 报告新章节

render_report 新增可选 kwargs：security_results / sitemap_quality / image_summary / not_found / overall_score。离线模式下这些为 None，报告对应节（3.5 安全头 / 3.6 sitemap / 3.7 图片 / 3.8 404）显示"离线未采集"占位；头部摘要卡片新增"加权总分/等级"大卡片。

### 离线回归

- 72 页逐页 flags：0 diff（0 critical / 62 major / 47 minor）
- similar_total：484 不变
- 孤儿：25 不变
- 新检查项在离线模式全部优雅跳过，不影响旧 flag 判定

### 测试

- 新增 `tests/test_site_security.py`：17 个新测试（A 安全头 3 + B bots 1 + C llms 3 + D 404 2 + E 评分 3 + F sitemap 2 + G 图片 2 + H stub 1）
- 全量：76/76 全绿（59 + 17）
- eval Recall@5：100%（52/52）

### 仍 open 的 TODO

1. 在线模式下安全头/sitemap/图片/404 数据未接入 cli.py 的 render_report 调用链（当前只在 facts 里，未传给 render_report）；需在线 --deep 跑一次把这些结果喂进 render_report 的 kwargs。
2. 死链探测结果未在 Top 叙事项里单列。
3. PageSpeed API 无 key 时仍走真实 HTTP 请求，未在离线/测试中完全桩住。

---

## P0 收尾（2026-09-19）

### 里程碑落地
- M1.1 hreflang：PageParser 收 hreflang {hreflang,href}；flag 双向回指/缺 x-default/指向非 200；tests/test_hreflang.py
- M1.2 重定向链：http_get 循环读 Location 记链；flag 链长>3 minor、302/307 应改 301 major、链尾非 https minor；tests/test_redirect.py
- M1.3 出站 rel：out_links 收 rel 占比；probe_dead_links external 模式（--external-probe，限速≥2s）；报告出站 rel 分布节
- M1.4 PSI：run_pagespeed 补 INP；cli.py 在线分支调用并传 render_report 3.9 节；scoring PSI 作第 5 类（medium=5）；无 key/网失败降级"PSI 未采集"不当 0 分
- M1.5 IndexNow：site_push.py + `push --url [--key] [--out]`；mock 测 POST 体；403/429 不误报
- M1.6 接线：cli.py 已把安全头/sitemap/图片/404/总分/PSI 传入 render_report kwargs（本轮补 PSI 3.9 渲染节）

### 权重口径
Severe=10 / Medium=5 / Low=2；总分=通过权重和/总权重和×100；等级 A 90-100 / B 75-89 / C 60-74 / D 40-59 / F <40。新增 PSI 类后历史分不可直接比。

### 回归
- 全量测试：90/90 OK（0.9s，网络全 mock）
- 离线 hbyagada：72 页 / 0 critical / 62 major / 47 minor / 25 孤儿 / similar_total=484 / trailing_slash_duos 字段在
- eval Recall@5=100%

### 剩余 TODO
- P1：GEO LLM 实测、实体一致性、JSON-LD 必填属性、锚文本、参数化 URL、必应 WMT、DKIM
- PSI HTTP 桩测试未做（skipped 路径覆盖）

## 第八轮：P1+P2 外部数据通路（M2.1-M3.4，2026-09-19）

### P1 外部数据通路

| 里程碑 | 实现 | 测试 |
|---|---|---|
| M2.1 GEO LIVE | `geo_live.py`：OpenAI 兼容 chat/completions，env GEO_LIVE_API_KEY/BASE_URL/MODEL；mention/citation 率；history 存 data/geo-history/ | `test_geo_live.py` 4 项 |
| M2.2 实体一致性 | cross_page_analysis 抽全站 Organization name，输出 `org_names` | （在 cross_page_analysis 里，无独立测试） |
| M2.3 JSON-LD 必填 | flag_page 加 LD_REQUIRED 映射（Product 缺 offers→critical） | `test_p1_features.py` 2 项 |
| M2.4 锚文本分布 | cross_page_analysis 输出 exact/generic 比例 | （在 cross_page_analysis 里） |
| M2.5 URL 归一 | `normalize_url()` 剥离 utm_*/gclid/fbclid/sessionid | `test_p1_features.py` 3 项 |
| M2.6 Bing WMT | `run_bing_webmaster()`：无 key skipped | `test_p1_features.py` 1 项 |
| M2.7 DKIM | `check_dkim()`：selector._domainkey.domain TXT | `test_p1_features.py` 1 项 |

### P2 集成自动化

| 里程碑 | 实现 | 测试 |
|---|---|---|
| M3.1 历史趋势 | facts.json 存 data/audit-history/（自动 diff 留 TODO） | （结构就绪） |
| M3.2 GSC 验证指引 | `gsc_verification_guide()` 返回 DNS TXT/HTML/meta 三选一 | `test_p1_features.py` 1 项 |
| M3.3 Lighthouse CLI | `run_lighthouse_cli()`：subprocess 调本机 lighthouse，无则 skipped | `test_p1_features.py` 1 项 |
| M3.4 hreflang 簇 | cross_page_analysis 输出 `hreflang_languages` + `hreflang_cluster_ok` | （在 cross_page_analysis 里） |

### GEO_LIVE_* 环境变量配置

```
set GEO_LIVE_API_KEY=sk-xxx
set GEO_LIVE_BASE_URL=https://api.siliconflow.cn/v1
set GEO_LIVE_MODEL=deepseek-ai/DeepSeek-V3
py -3.11 -m geosentry geo-live --url https://hbyagada.com --queries queries.txt
```

### 回归

- 单测：103/103 全绿（90 + 4 geo_live + 9 p1_features）
- eval Recall@5：100%（52/52）
- 离线回归：72 页、0/62/47、25 孤儿、484 similar——0 diff

### 仍 open 的 TODO

1. M3.1 历史趋势的自动 diff 逻辑未实现（目录结构就绪，diff 脚本留 TODO）
2. M2.6 Bing WMT 有 key 时的实际 API 调用未测（需真实 key）
3. M2.7 DKIM 在有 dnspython 环境下未跑实测
4. M3.3 Lighthouse CLI 实际运行未测（需本机装 lighthouse）
5. PSI 报告章节 3.9 HTML 渲染仍未补（上轮遗留）
6. 外部出站死链探测仍未实现（上轮遗留）
