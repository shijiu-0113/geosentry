"""网络连通性探测：确认哪些数据源可访问，供爬取脚本选择。"""
import urllib.error
import urllib.request
import socket

socket.setdefaulttimeout(8)

URLS = [
    ("google-cn", "https://developers.google.cn/search/docs/fundamentals/ai-optimization-guide?hl=zh-cn"),
    ("google-com", "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide"),
    ("mdn", "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta"),
    ("llmstxt", "https://llmstxt.org/"),
    ("arxiv", "https://arxiv.org/abs/2311.09735"),
    ("pypi", "https://pypi.org/"),
    ("github", "https://github.com/"),
    ("huggingface", "https://huggingface.co/"),
    ("baidu", "https://www.baidu.com/"),
]

def probe(name, url):
    req = urllib.request.Request(url, headers={"User-Agent": "geosentry-probe/0.1 (research; contact: dev@example.com)"})
    try:
        with urllib.request.urlopen(req) as r:
            print(f"{name:14s} -> {r.status}  {url}")
    except urllib.error.HTTPError as e:
        print(f"{name:14s} -> HTTP {e.code}  {url}")
    except Exception as e:
        print(f"{name:14s} -> ERR {type(e).__name__}: {e}  {url}")

for name, url in URLS:
    probe(name, url)
