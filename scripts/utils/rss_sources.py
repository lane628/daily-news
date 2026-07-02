"""
RSS 信源配置
按板块分类的 RSS Feed 列表

domestic_available: 国内网络环境是否可用
  - True: 本地开发和 GitHub Actions 都可用
  - False: 仅在 GitHub Actions（海外服务器）可用
type: "rss" 或 "scrape"（网页爬取）
"""

SOURCES = {
    "internet": {
        "label": "🌐 互联网与商业",
        "feeds": [
            {
                "name": "36氪",
                "url": "https://36kr.com/feed",
                "lang": "zh",
                "type": "rss",
                "domestic_available": True,
            },
            {
                "name": "虎嗅",
                "url": "https://www.huxiu.com/rss/0.xml",
                "lang": "zh",
                "type": "rss",
                "domestic_available": False,
            },
            {
                "name": "晚点LatePost",
                "url": "https://www.latepost.com/rss",
                "lang": "zh",
                "type": "rss",
                "domestic_available": False,
            },
            {
                "name": "华尔街见闻",
                "url": "https://wallstreetcn.com/rss",
                "lang": "zh",
                "type": "rss",
                "domestic_available": False,
            },
        ],
    },
    "ai": {
        "label": "🤖 AI 前沿",
        "feeds": [
            {
                "name": "量子位",
                "url": "https://www.qbitai.com/feed",
                "lang": "zh",
                "type": "rss",
                "domestic_available": True,
            },
            {
                "name": "AI星球",
                "url": "https://aixq.cc/feed",
                "lang": "zh",
                "type": "rss",
                "domestic_available": True,
            },
            {
                "name": "Arxiv CS.AI",
                "url": "http://arxiv.org/rss/cs.AI",
                "lang": "en",
                "type": "rss",
                "domestic_available": True,
            },
            {
                "name": "机器之心",
                "url": "https://www.jiqizhixin.com/rss",
                "lang": "zh",
                "type": "rss",
                "domestic_available": False,
            },
            {
                "name": "The Verge - AI",
                "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
                "lang": "en",
                "type": "rss",
                "domestic_available": False,
            },
        ],
    },
    "finance": {
        "label": "💰 金融市场",
        "feeds": [
            {
                "name": "同花顺",
                "url": "https://news.10jqka.com.cn/",
                "lang": "zh",
                "type": "scrape",
                "domestic_available": True,
            },
            {
                "name": "东方财富",
                "url": "https://rsshub.app/eastmoney/report",
                "lang": "zh",
                "type": "rss",
                "domestic_available": False,
            },
            {
                "name": "雪球",
                "url": "https://rsshub.app/xueqiu/today",
                "lang": "zh",
                "type": "rss",
                "domestic_available": False,
            },
            {
                "name": "新浪财经",
                "url": "https://rsshub.app/sina/finance",
                "lang": "zh",
                "type": "rss",
                "domestic_available": False,
            },
            {
                "name": "Yahoo Finance",
                "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
                "lang": "en",
                "type": "rss",
                "domestic_available": False,
            },
        ],
    },
}
