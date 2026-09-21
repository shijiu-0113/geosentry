# GeoSentry · 本机 SEO/GEO 全站审计与 RAG 知识背板

把 Google 官方 SEO / GEO 文档语料做成**可检索的本地知识背板**：零部署、零第三方依赖（纯 Python 标准库），回答"某个 SEO/GEO 问题，Google 官方文档怎么说"，每条结果自带出处与章节，可追溯。

数据支撑：**39 篇语料**（Google Search Central 官方文档 33 篇 + MDN 3 篇 + GEO 生态 3 篇），覆盖 2026 年最新官方口径（ai-optimization-guide、spam-policies 含 site reputation policy 的 EEA 更新、preferred sources、生成式 AI 性能报告等）。

---

## 快速开始（30 秒）

```powershell
cd C:\Users\shijiu\Desktop\geosentry

# 1. 建索引（一次）
py -3.11 -m geosentry index

# 2. 提问（中英文都可以）
py -3.11 -m geosentry search "llms.txt 影响 Google 排名吗" --top-k 5
py -3.11 -m geosentry search "how to control AI crawlers with robots.txt"

# 3. 站点 GEO 审计
py -3.11 -m geosentry audit --url https://你的网站.com

# 4. 查看状态
py -3.11 -m geosentry info
```

> 环境要求：仅 Python ≥ 3.10。索引数据在 `data/`，删除后重新 `index` 即可重建。

## Python 代码里用

```python
from geosentry import GeoSentry

bp = GeoSentry()                      # 自动加载 data/ 索引
results = bp.search("什么是 helpful content？", top_k=5)
for r in results:
    print(r["doc"], r["url"], r["heading"])
    print(r["text"][:200])
```

## 检索原理

混合检索 + 加权 RRF 融合，**向量（TF-IDF）∥ BM25 双通道**：

```
查询 → 中文 bigram / 英文单词（停用词过滤 + 领域同义扩展 + 编辑距离容错）
        ├─ 向量通道：TF-IDF 稀疏向量余弦 top-K
        └─ BM25 通道：Okapi BM25 相关度 top-K
              ↓ 加权 RRF 融合 (k=20, weights=(1.0,1.0)，扫参选定)
        带出处结果（doc / url / 章节 / 原文片段）
```

- **切块**：H2/H3 语义切分；fenced code block 原子保护（不在 fence 内 flush）；chunk 正文前自动拼标题面包屑（`H1 > H2 > H3`），让向量与 BM25 都能看到章节上下文。
- **中文友好**：每篇文档配有**中文检索标签**（`corpus/doc_labels_zh.json`），中文提问可直接命中官方英文文档，展示仍为官方原文。
- **RRF 扫参**：`eval/sweep.py` 对 k∈{20,60,100} × weights∈{(1,1),(1.5,1),(1,1.5)} 跑 52 题，实测 k=20 全权重组合均 100%，定稿为默认。

## 数据支撑（39 篇）

| 分级 | 目录 | 内容 | 篇数 |
|---|---|---|---|
| A | `corpus/google-docs/` | Google Search Central 官方文档（robots/sitemap/canonical/结构化数据/helpful content/JavaScript SEO 等） | 30 |
| B | `corpus/google-docs/` | 2026 新增高价值官方文档：ai-optimization-guide、spam-policies（含 site reputation policy + EEA 更新）、preferred-sources、gen-ai-performance-reports | 3 |
| C | `corpus/mdn-docs/` | MDN 技术规范（title/meta/link 元素） | 3 |
| D | `corpus/geo-knowledge/` | GEO 生态（非官方，检索/审计时标注）：llms.txt 规范、AI 爬虫清单、GEO 起源论文（arXiv:2311.09735） | 3 |

**2026 官方口径要点**（已内置，检索可复现）：
- llms.txt **不**影响 Google 排名（官方明确"Google Search 不使用这些文件"）；无需为 AI 切块（chunking）
- AEO/GEO 官方视角**仍是 SEO**；AI Overviews / AI Mode 基于核心搜索索引 + RAG
- spam 政策适用于生成式 AI 回答；site reputation policy 2026-08-28 更新 EEA 处理方式
- preferred sources：Top Stories / AI Mode / AI Overviews 可用，域名/子域名级参与
- Search Console 2026-06 上线生成式 AI 性能报告

## 数据量大怎么办（升级阶梯，接口不变）

| 规模 | 方案 | 说明 |
|---|---|---|
| ~1 万 chunk | **当前默认**（纯 stdlib 稀疏向量 + BM25） | 检索毫秒级 |
| ~50 万 chunk | 嵌入式向量库 | 换后端，`search()` 接口不变 |
| ~100 万 chunk | 量化向量（PQ/OPQ） | 内存减 8 倍 |
| 千万级 | RAGFlow / Elasticsearch | 集群部署 |

`GeoSentry` 的 `index()` / `search()` 是唯一接口，后端替换不影响调用方。

## 可选增强

```powershell
# 语义向量（效果最佳）：申请 SiliconFlow API Key 后设置环境变量
$env:SILICONFLOW_API_KEY = "sk-..."   # 然后重新 index
# 自动启用 Qwen3-Embedding-8B；无 Key 时自动回退 TF-IDF

# 可选依赖（不装不影响核心功能）
py -3.11 -m pip install numpy        # 向量计算加速
py -3.11 -m pip install trafilatura  # 爬虫 HTML→Markdown 更精准
```

## 增量爬取语料

```powershell
py -3.11 scripts/crawl_docs.py --source google --limit 5
```

内置：robots.txt 门禁（尊重 Disallow）、1 req/s 限速、HTML→Markdown 转换、已存在文件跳过。注意：
- **本机网络对 developers.google.com 直连受限**（IP 层超时），新增 Google 官方文档用工具通道抓取后放入 `corpus/google-docs/`（格式：文件名小写连字符 `.md`，头部含来源/更新时间 frontmatter），再 `index` 重建。
- 爬虫 UA 中的联系邮箱（`research@example.com`）为占位，**正式使用前请替换为真实邮箱**（合规要求，见 `scripts/crawl_docs.py` 顶部 `UA`）。

## 评测

```powershell
py -3.11 eval\run_eval.py
py -3.11 eval\sweep.py          # RRF k/权重扫参，打印 Recall@5 矩阵
```

52 道 QA 评测题（覆盖全部 39 篇文档），结果：
- **Recall@5 = 100%**（52/52 命中目标文档，门禁 ≥90% ✅）
- 关键词命中率 ~89%（片段内出现期望关键词）

单元测试：

```powershell
py -3.11 -m unittest discover -s tests -v
```

## 站点审计

`audit --url <site>` 跑 13 项基础检查（robots/title/meta/H1/正文字数/JSON-LD/llms.txt/canonical/OG/sitemap/viewport/charset/HTTPS），并额外输出：
- **AI 爬虫放行明细**：逐 bot（GPTBot / ClaudeBot / Claude-Web / PerplexityBot / Google-Extended）报告 robots.txt 对 `/` 路径的 allow/disallow。
- **llms.txt 结构校验**：首行 `# 标题`、`> blockquote` 摘要、`- [title](绝对URL)` 列表、URL 无重复。

SSL 默认校验证书；自签名/内网测试站加 `--no-verify-ssl`。

### 全站逐页深审（--deep）

`audit --deep` 在轻量单页审计之上增加**全站逐页**能力：BFS 爬取 sitemap + 内链发现、robots 门禁、限速、抓 HTML/PDF 存 `raw/`，逐页分析（HTTP 状态 / title / description / H1 / 正文字数 / canonical / JSON-LD / 内链图 / 近似内容聚类 / 孤儿页 / 死链 / PDF 卫生），并从 `facts.json` 自动生成**深色主题单文件 HTML 报告**。

```powershell
# 在线深审（真实爬网）
py -3.11 -m geosentry audit --url https://目标站.com --deep --out docs/site-audit-my/

# 离线模式（不联网，直接分析本地 raw/ 目录，验证/复跑用）
py -3.11 -m geosentry audit --url https://目标站.com --deep `
    --offline docs/site-audit-my/raw --out docs/site-audit-my/
```

产出目录：
- `data/facts.json` — 机器判定事实表（rows/issues_count/orphans/similar_top/pdfs）
- `data/pages.json` — 每页原始解析信号（在线模式才有）
- `audit-report.html` — 深色主题单文件报告（头部摘要卡片 → 一句话结论 → Top 优先级问题 → 全站分析 → 逐页明细表 → PDF 汇总 → P0/P1/P2 路线图）

判定阈值：title >65 字符 major、<25 minor；description >170/<70 minor；正文 <300 major、<600 minor；无 H1 major；非 200 critical；canonical 缺失 critical、未自指 major；相似内容 Jaccard ≥0.5 报告、≥0.9 标 doorway 风险；孤儿页入链 ≤1。
### P0 增强（v2 检查集）

在 --deep 之上新增：
- **hreflang 校验**：双向回指（A→B 则 B→A）、缺 x-default major、指向非 200 major（离线跳过）
- **重定向链**：完整 Location 链记录；链长 >3 minor、302/307 应改 301 major、链尾非 https minor
- **出站 rel 分布**：nofollow/sponsored/ugc 占比成节
- **死链在线探测**：默认对内部未知 href 探测；加 `--external-probe` 开外链探测（限速 ≥2s）
- **安全响应头**：HSTS/CSP severe、X-Frame-Options/nosniff medium、Referrer/Permissions/COOP/COEP/CORP low
- **sitemap 质量**：XML 有效/含 url/有 lastmod/robots 声明/隐私法律页不泄露
- **图片优化**：width/height、WebP/AVIF、非首图 lazy、fetchpriority、alt
- **软 404**：随机 path 探测（200 即 Fail）、自定义 404 正文 >200 字、含回首页链接
- **加权总分**：Severe=10 / Medium=5 / Low=2；总分=通过权重和/总权重和×100；等级 A 90-100 / B 75-89 / C 60-74 / D 40-59 / F <40；报告头部大卡片
- **PageSpeed Insights（报告 3.9 节）**：Performance/Accessibility/Best Practices/SEO 四类分 + LCP/CLS/FCP/TTFB/INP 五指标；PSI 作第 5 类并入加权（medium=5）；无 key/无网显示"PSI 未采集"不当 0 分

### IndexNow 推送（push）

```powershell
# 把 facts.json 里的 URL 列表 POST 到 api.indexnow.org
py -3.11 -m geosentry push --url https://目标站.com --key <your-key> --out docs/site-audit-my/
```
首次运行会提示在站点根目录放 `<key>.txt`；HTTP 403/429 不误报成功。

## 目录结构

```
geosentry/
├── geosentry/                  # 核心包（纯 stdlib）
│   ├── __init__.py             # GeoSentry 主类（index/search/info）
│   ├── __main__.py             # python -m geosentry 入口
│   ├── cli.py                  # index/search/audit/crawl/info 子命令
│   ├── chunker.py              # Markdown 切块（H2 语义切分 + frontmatter 元数据）
│   ├── bm25.py                 # Okapi BM25（中英分词）
│   ├── vectorizer.py           # TF-IDF（默认）/ SiliconFlow API（可选）
│   ├── retriever.py            # 向量∥BM25 → RRF 融合
│   ├── store.py                # data/ 持久化
│   ├── geo_audit.py            # 站点 GEO/SEO 基础审计（对照官方文档）
│   ├── site_crawler.py         # 全站 BFS 爬取（sitemap + robots 门禁 + 限速）
│   ├── site_audit.py           # 逐页分析 + 跨页聚类 + 问题 flag（支持离线 raw/）
│   └── report_html.py          # 深色主题单文件 HTML 报告生成器
├── corpus/
│   ├── google-docs/            # A/B 级：Google 官方文档 33 篇
│   ├── mdn-docs/               # C 级：MDN 3 篇
│   ├── geo-knowledge/          # D 级：GEO 生态 3 篇（非官方）
│   └── doc_labels_zh.json      # 文档中文检索标签
├── scripts/
│   ├── crawl_docs.py           # 增量爬取（robots 门禁 + 限速）
│   ├── fetch_geo_knowledge.py  # 抓取 llmstxt.org / arXiv 摘要
│   ├── net_probe.py            # 网络连通性探测
│   └── debug_queries.py        # 检索通道调试
├── eval/
│   ├── qa_seed.jsonl           # 52 题评测集
│   ├── run_eval.py             # Recall@5 评测（门禁 90%）
│   └── sweep.py                # RRF k/权重扫参
├── tests/test_geosentry.py     # 25 项单元测试（RAG 核心）
├── tests/test_site_audit.py    # 20 项单元测试（全站深审）
├── data/                       # 生成物：索引（可删除重建）
├── pyproject.toml
└── README.md
```

## 合规与免责

- 内置语料来自 Google Search Central / MDN / llmstxt.org / arXiv 公开文档，仅作本地检索学习用途；转载引用请遵守各站条款。
- `corpus/geo-knowledge/` 内容为**非官方** GEO 生态实践（llms.txt 规范、AI 爬虫清单、论文摘要），检索结果中 `source: geo` 即为此类，请与官方文档区分。
- 审计结果基于公开可访问内容自动检查，不构成 SEO 承诺。
