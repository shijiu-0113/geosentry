---
title: AI 爬虫清单与 robots.txt 放行指南
url: https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers
source: geo-knowledge（非官方，综合各厂商公开说明）
---
# AI 爬虫清单与 robots.txt 放行指南

> 类型：GEO 生态实践（非 Google 官方文档，综合各厂商公开说明）
> 主要参考：Cloudflare 博客（2025-07）、各厂商官方 robots/爬虫说明页、社区指南

AI 搜索引擎/大模型通过各自的爬虫抓取网页用于训练或检索引用。控制 robots.txt 中这些 UA 的访问，是 GEO 的第一步：**如果爬虫被 Disallow，你的内容在该 AI 平台上完全没有被引用的机会**。

## 主要 AI 爬虫清单

| User-agent | 运营方 | 用途 | 说明 |
|---|---|---|---|
| GPTBot | OpenAI | 训练数据采集 | 尊重 robots.txt Disallow |
| OAI-SearchBot | OpenAI | 索引网页供 ChatGPT 搜索引用 | 与 GPTBot 相互独立，需单独配置 |
| ChatGPT-User | OpenAI | 用户提问时实时抓取页面 | 用户主动触发，robots 规则可能不适用 |
| OAI-AdsBot | OpenAI | 广告落地页安全检查 | 只访问提交的广告页 |
| ClaudeBot | Anthropic | 采集文本训练 Claude | 尊重 robots.txt |
| Claude-SearchBot / claude-search | Anthropic | Claude 搜索引用 | 检索类爬虫 |
| anthropic-ai | Anthropic | 训练与检索 | 可一并配置 |
| PerplexityBot | Perplexity | 索引网页供 Perplexity 回答引用 | 尊重 robots.txt |
| PerplexityBot-User | Perplexity | 用户触发抓取 | |
| Google-Extended | Google | Gemini 训练/grounding 的退出控制 token | 阻止它不影响 Google 搜索收录 |
| Googlebot | Google | 搜索收录 | AI Overviews / AI Mode 依赖其索引 |
| Bingbot / Bingbot-User | Microsoft | Bing 收录 + Copilot 引用 | |
| Applebot-Extended | Apple | Apple Intelligence 训练 | 与 Applebot 独立 |
| Amazonbot | Amazon | 产品信息采集 | |
| Meta-ExternalAgent | Meta | AI 助手检索 | |
| Bytespider | 字节跳动 | 豆包等训练/检索 | |
| CCBot | Common Crawl | 开放爬取数据 | |
| cohere-ai | Cohere | 训练/检索 | |
| Xenobot / xAI | xAI | Grok 检索 | |
| DuckAssistBot | DuckDuckGo | AI 助手 | |
| Vercelbot / AhrefsBot 等 | SEO 工具 | 分析 | 非 AI 引擎，按需处理 |

## robots.txt 放行示例（全放行）

```text
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /
```

## 阻止示例（全部阻止 AI 爬虫）

```text
User-agent: GPTBot
Disallow: /

User-agent: OAI-SearchBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Claude-SearchBot
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Google-Extended
Disallow: /
```

注意：阻止 Google-Extended 只影响 Gemini 训练/grounding，不影响 Google 搜索索引；阻止 Googlebot 才会影响搜索收录与 AI Overviews 数据源。

## 要点

- 各 AI 引擎的爬虫清单会持续变化，部署前以各厂商最新说明为准。
- 部分引擎（如 ChatGPT-User）是用户触发抓取，robots.txt 不一定适用，内容可见性仍需依赖公开可访问。
- AI Overviews / AI Mode 的引用来源以 Google 搜索索引为基础，因此 Googlebot 的放行优先级最高。
