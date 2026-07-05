#!/usr/bin/env python3
"""
每日新闻抓取脚本
遍历各信源 RSS/Feed + 同花顺网页爬取，提取文章并调用 DeepSeek API 生成摘要
输出：content/daily/YYYY/MM/YYYY-MM-DD.md
"""

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from utils.rss_sources import SOURCES
from utils.llm_summarizer import summarize_article


def extract_image_from_entry(entry) -> str:
    """
    从 RSS entry 中提取首张图片 URL

    优先级：media_content > enclosures > summary/content 中的 img 标签
    """
    # 1. media:content
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            if media.get("medium") == "image" or "image" in media.get("type", ""):
                return media.get("url", "")

    # 2. enclosures
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href", "")

    # 3. summary/content 中的 img 标签
    html = ""
    if hasattr(entry, "summary"):
        html = entry.summary
    elif hasattr(entry, "content") and entry.content:
        html = entry.content[0].value

    if html:
        soup = BeautifulSoup(html, "lxml")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    return ""


def fetch_feed(feed_config: dict, target_date: str) -> list:
    """
    抓取单个 RSS Feed 的文章

    Args:
        feed_config: 信源配置 {"name", "url", "lang", "type", "domestic_available"}
        target_date: 目标日期 "YYYY-MM-DD"

    Returns:
        文章列表
    """
    print(f"  抓取: {feed_config['name']} ({feed_config['url']})")
    articles = []

    try:
        feed = feedparser.parse(feed_config["url"])
        if feed.bozo and not feed.entries:
            print(f"    [WARNING] Feed 解析异常: {feed_config['name']}")
            return []

        for entry in feed.entries[:15]:  # 每个信源最多取 15 条
            # 提取发布时间
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d")

            # 只保留目标日期当天和前一天的文章
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            if pub_date:
                pub_dt = datetime.strptime(pub_date, "%Y-%m-%d")
                if pub_dt < target_dt - timedelta(days=1):
                    continue
                if pub_dt > target_dt:
                    continue

            # 提取图片
            image_url = extract_image_from_entry(entry)

            # 提取内容
            content = ""
            if hasattr(entry, "summary"):
                content = entry.summary
            elif hasattr(entry, "content"):
                content = entry.content[0].value if entry.content else ""

            # 清理 HTML 标签
            content_text = BeautifulSoup(content, "lxml").get_text()[:2000]

            articles.append({
                "title": entry.get("title", "无标题"),
                "content": content_text,
                "image_url": image_url,
                "source": feed_config["name"],
                "source_url": entry.get("link", ""),
                "lang": feed_config["lang"],
                "date": pub_date or target_date,
            })

    except Exception as e:
        print(f"    [ERROR] 抓取失败: {e}")

    return articles


def fetch_10jqka(target_date: str) -> list:
    """
    从同花顺新闻页面爬取金融新闻

    Args:
        target_date: 目标日期 "YYYY-MM-DD"

    Returns:
        文章列表
    """
    print(f"  爬取: 同花顺 (https://news.10jqka.com.cn/)")
    articles = []

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://news.10jqka.com.cn/",
        }
        resp = requests.get("https://news.10jqka.com.cn/", headers=headers, timeout=15)
        # 同花顺网页使用 GBK 编码
        resp.encoding = "gbk"

        if resp.status_code != 200:
            print(f"    [WARNING] HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        # 提取新闻列表（同花顺首页常见选择器）
        news_links = soup.select("a[href*='10jqka.com.cn']")

        seen_titles = set()
        for link in news_links:
            title = link.get_text(strip=True)
            href = link.get("href", "")

            # 过滤：标题太短、非新闻链接
            if len(title) < 8 or not href.startswith("http"):
                continue

            # 清洗标题：去编号、时间标记
            title = re.sub(r"^\[?\d+[\.、\]]\s*", "", title)
            title = re.sub(r"\s*\d{2}:\d{2}\s*$", "", title)
            title = title.strip()

            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            articles.append({
                "title": title,
                "content": "",
                "image_url": "",
                "source": "同花顺",
                "source_url": href,
                "lang": "zh",
                "date": target_date,
            })

            if len(articles) >= 15:
                break

    except Exception as e:
        print(f"    [ERROR] 同花顺爬取失败: {e}")

    return articles


def generate_markdown(all_news: dict, target_date: str) -> str:
    """
    生成当日新闻的 Markdown 文件内容
    支持图片左侧布局，动态缩进（items 10+ 时4空格对齐）
    """
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekdays[dt.weekday()]

    # Front Matter
    front_matter = {
        "title": f"{target_date} 每日早报",
        "date": target_date,
        "draft": False,
    }

    lines = ["---"]
    lines.append(yaml.dump(front_matter, allow_unicode=True, default_flow_style=False).strip())
    lines.append("---\n")

    # 分类对应渐变占位图 class
    category_placeholder = {
        "internet": "placeholder-internet",
        "ai": "placeholder-ai",
        "finance": "placeholder-finance",
    }
    category_emoji = {
        "internet": "🌐",
        "ai": "🤖",
        "finance": "💰",
    }

    # 各板块内容
    for category, config in SOURCES.items():
        label = config["label"]
        news_items = all_news.get(category, [])

        lines.append(f"### {label}\n")

        if not news_items:
            lines.append("暂无更新\n")
            continue

        for i, item in enumerate(news_items, 1):
            image_html = ""
            if item.get("image_url"):
                image_html = f'<img src="{item["image_url"]}" alt="" loading="lazy">'
            else:
                emoji = category_emoji.get(category, "📰")
                ph_class = category_placeholder.get(category, "placeholder-internet")
                image_html = f'<div class="placeholder {ph_class}">{emoji}</div>'

            # 动态缩进：序号 >= 10 时用4空格对齐
            idx_str = f"[{i}]"

            lines.append(f'<div class="news-item">')
            lines.append(f'<div class="news-image">{image_html}</div>')
            lines.append(f'<div class="news-body">')
            lines.append(f'<div class="news-title"><a href="{item["source_url"]}">{idx_str} {item["title"]}</a> <span class="news-source-tag">{item["source"]}</span></div>')
            lines.append(f'<div class="news-summary">{item.get("summary", "")}</div>')
            lines.append(f'</div>')
            lines.append(f'</div>\n')

    return "\n".join(lines)


def main():
    """主流程"""
    # 目标日期（默认昨天）
    target_date = os.environ.get("NEWS_DATE", "").strip()
    if not target_date:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"=== 每日新闻抓取 · 目标日期: {target_date} ===\n")

    all_news = {}

    for category, config in SOURCES.items():
        print(f"\n【{config['label']}】")
        category_articles = []

        for feed_config in config["feeds"]:
            if feed_config.get("type") == "scrape":
                # 网页爬取（同花顺）
                if "10jqka" in feed_config["url"]:
                    articles = fetch_10jqka(target_date)
                else:
                    articles = []
            else:
                # RSS 抓取
                articles = fetch_feed(feed_config, target_date)

            category_articles.extend(articles)

        # 去重（按标题）
        seen_titles = set()
        unique_articles = []
        for a in category_articles:
            if a["title"] not in seen_titles:
                seen_titles.add(a["title"])
                unique_articles.append(a)

        # 调用 LLM 生成摘要（限制每板块最多 15 条）
        unique_articles = unique_articles[:15]
        print(f"  共 {len(unique_articles)} 条，生成摘要中...")

        for article in unique_articles:
            try:
                article["summary"] = summarize_article(
                    article["title"],
                    article["content"],
                    article["lang"]
                )
            except Exception as e:
                print(f"    [WARNING] 摘要生成异常: {e}")
                fallback = article["content"][:150].strip()
                article["summary"] = (fallback + "...") if fallback else article["title"]

        all_news[category] = unique_articles

    # 生成 Markdown 文件
    md_content = generate_markdown(all_news, target_date)

    # 写入文件
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    output_dir = Path(__file__).parent.parent / "content" / "daily" / str(dt.year) / f"{dt.month:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{target_date}.md"

    output_file.write_text(md_content, encoding="utf-8")
    print(f"\n✅ 输出文件: {output_file}")

    # 同时输出结构化数据（供搜索索引使用）
    import json
    index_data = []
    idx = 0
    for category, articles in all_news.items():
        for article in articles:
            idx += 1
            index_data.append({
                "id": idx,
                "title": article["title"],
                "summary": article.get("summary", ""),
                "image_url": article.get("image_url", ""),
                "date": article.get("date", target_date),
                "category": category,
                "source": article["source"],
                "source_url": article["source_url"],
            })

    json_output = Path(__file__).parent.parent / "static" / f"news-{target_date}.json"
    json_output.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 结构化数据: {json_output}")


if __name__ == "__main__":
    main()
