# GeoSentry · Local SEO/GEO Site Auditor

**本机运行的全站 SEO/GEO 审计工具。** 填一个 URL，30 秒出全站逐页报告：title / H1 / 结构化数据 / 安全头 / 死链 / AI 爬虫权限 / 性能分，A-F 加权评分，深色玻璃拟态 Web UI。

**零依赖、不上云、不开源费。** 纯 Python 标准库，客户数据不出服务器。

---

## 30 秒跑起来

```bash
# 1. clone
git clone https://github.com/shijiu-0113/geosentry.git
cd geosentry

# 2. 启动 Web UI（浏览器自动打开）
py -3.11 -m geosentry serve
```

浏览器打开 **http://127.0.0.1:8765**，填 URL → 点开始 → 看实时进度条 + 报告。

**环境要求：** Python 3.11+。不需要 pip install 任何东西。

> Linux 服务器上如果报 SSL 证书错误，先 `apt install ca-certificates`，或启动时加 `--no-verify-ssl`。

---

## Web UI 用法

| 字段 | 默认 | 说明 |
|---|---|---|
| URL | 必填 | 目标站，如 `https://example.com` |
| 全站深审 | ✅ | 爬整站逐页分析；取消则只审首页 |
| 并发 | 2 | 建议 1-4，太大会被目标站封 |
| 磁盘缓存 | ✅ | 二次审计不重新下载，快很多 |
| 死链上限 | 50 | 探测多少个未知内部链接；0 = 不限 |
| HTTP 代理 | 空 | 国内访问 Google PSI 填 `http://127.0.0.1:7890` |

跑完自动生成深色 HTML 报告，嵌在页面里，可全屏看、可新窗口打开、可打印为 PDF。

---

## CLI 用法

```bash
# 全站深审（最常用）
py -3.11 -m geosentry audit --url https://example.com --deep

# 自定义输出目录 + 并发
py -3.11 -m geosentry audit --url https://example.com --deep --out ./my-audit --concurrency 2

# 单页轻量审
py -3.11 -m geosentry audit --url https://example.com/about

# 离线模式（不联网，分析本地已抓的 HTML）
py -3.11 -m geosentry audit --url https://example.com --deep --offline ./my-audit/raw --out ./my-audit

# 启动 Web UI
py -3.11 -m geosentry serve --port 8765 --host 0.0.0.0

# 单元测试
py -3.11 -m unittest discover -s tests
```

**常用参数：**

| 参数 | 说明 |
|---|---|
| `--deep` | 全站逐页爬取（不加只审单页） |
| `--out DIR` | 输出目录 |
| `--concurrency N` | 并发线程数（默认 1，礼貌） |
| `--max-dead-probes N` | 死链探测上限（默认 50，0=不限） |
| `--no-verify-ssl` | 跳过 SSL 证书校验 |
| `--external-probe` | 死链探测也覆盖外链 |
| `--delay SEC` | 请求间隔秒数（默认 1.2） |

---

## 审计查什么（40+ 项）

**逐页检查：**
- `<title>` 长度 30-60、唯一
- `<meta description>` 长度 120-160
- 唯一 `<h1>`、标题层级不跳级
- canonical URL、Open Graph、Twitter Card
- viewport、`html lang`、charset
- JSON-LD 结构化数据可解析
- 图片 alt 文本覆盖率、width/height 属性
- 正文词数（< 300 词判 thin content）

**跨页检查：**
- 重复 title / meta description
- 孤儿页（无内链指向）
- 死链在线探测（HTTP 4xx）
- 软 404 检测
- sitemap XML 有效性
- robots.txt 对 AI 爬虫逐 UA 报告（GPTBot / ClaudeBot / PerplexityBot / Google-Extended）
- llms.txt 结构校验

**全站检查：**
- HTTPS 有效证书
- 安全头：HSTS / CSP / X-Frame-Options / nosniff / Referrer-Policy / Permissions-Policy
- 图片格式（WebP/AVIF）、lazy loading
- 404 页面内容
- PageSpeed Insights（可选，Google API，6 秒超时自动跳过）

**评分：** severe=10 / medium=5 / low=2；A 90-100 / B 75-89 / C 60-74 / D 40-59 / F <40。

---

## RAG 知识背板（进阶）

内置 39 篇 SEO/GEO 官方文档（Google Search Central 33 篇 + MDN 3 篇 + GEO 生态 3 篇），建索引后可以直接问：

```bash
py -3.11 -m geosentry index    # 建索引，跑一次就行
py -3.11 -m geosentry search "llms.txt 影响 Google 排名吗"
py -3.11 -m geosentry search "how to control AI crawlers"
```

混合检索：TF-IDF ∥ BM25 → 加权 RRF 融合。Recall@5 = 100%（52 题评测）。

> 网站审计功能不依赖索引，跳过这步直接用 Web UI 就行。

---

## 输出文件

```
my-audit/
├── audit-report.html   ← 主交付物，单文件 HTML，浏览器直接打开
├── data/
│   ├── facts.json      ← 机器可读（给其他 agent / 脚本用）
│   └── pages.json      ← 每页原始解析数据
└── raw/                ← 抓下来的原始 HTML
```

---

## 技术特点

- **纯 Python 标准库**，零 pip 依赖
- **本地运行**，不向第三方发送任何数据
- **可被 AI agent 集成**：见 `AGENT_MANUAL.md`
- **深色玻璃拟态 Web UI**，实时进度条 + 日志
- 支持 HTTP 代理（国内访问 Google PSI）

---

## 目录结构

```
geosentry/
├── geosentry/           # 核心包
│   ├── cli.py           # 命令行入口
│   ├── web.py           # Web UI
│   ├── site_crawler.py  # 全站爬虫
│   ├── site_audit.py    # 逐页分析
│   ├── report_html.py   # HTML 报告生成
│   ├── site_security.py # 安全头检查
│   ├── scoring.py       # A-F 加权评分
│   └── ...
├── corpus/              # RAG 语料（39 篇官方文档）
├── tests/               # 单元测试
├── eval/                # 评测集
├── AGENT_MANUAL.md      # 给 AI agent 的调用手册
├── pyproject.toml
└── README.md
```

---

## License

MIT。审计结果基于公开可访问内容自动检查，不构成 SEO 承诺。
