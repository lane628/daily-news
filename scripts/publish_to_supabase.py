#!/usr/bin/env python3
"""Publish the daily-news ingestion result to the NoCode Supabase database.

This program runs in GitHub Actions, never in the browser. It keeps source
requests, summarisation and database credentials on the server side.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.path.dirname(__file__))
from fetch_news import fetch_10jqka, fetch_feed  # noqa: E402
from utils.llm_summarizer import summarize_article  # noqa: E402
from utils.rss_sources import SOURCES  # noqa: E402

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
TIMEOUT_SECONDS = 20
MAX_ITEMS_PER_SOURCE = 10


def headers(prefer: str | None = None) -> dict[str, str]:
    result = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        result["Prefer"] = prefer
    return result


def normalize_url(value: str) -> str:
    """Produce a stable URL key while retaining meaningful query parameters."""
    parsed = urlparse(value.strip())
    tracking_keys = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "ref"}
    query = urlencode(
        sorted((key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() not in tracking_keys)
    )
    return urlunparse(("", parsed.netloc.lower().removeprefix("www."), parsed.path.rstrip("/"), "", query, "")).lower()


def title_hash(title: str) -> str:
    normalized = re.sub(r"[\W_]+", "", title.lower())[:80]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def request(method: str, table: str, *, params: dict[str, str] | None = None, payload: Any = None, prefer: str | None = None) -> Any:
    response = requests.request(
        method,
        f"{SUPABASE_URL}/rest/v1/{table}",
        params=params,
        json=payload,
        headers=headers(prefer),
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def get_or_create_brief(date_value: str) -> int:
    existing = request("GET", "daily_briefs", params={"select": "id", "brief_date": f"eq.{date_value}", "limit": "1"})
    if existing:
        return int(existing[0]["id"])

    brief_id = int(datetime.now(tz=ZoneInfo("Asia/Shanghai")).timestamp() * 1000)
    request(
        "POST",
        "daily_briefs",
        payload={"id": brief_id, "title": f"{date_value} 每日早报", "brief_date": date_value},
        prefer="return=representation",
    )
    return brief_id


def known_urls() -> set[str]:
    rows = request("GET", "crawl_dedup", params={"select": "normalized_url", "limit": "5000"})
    return {str(row["normalized_url"]) for row in rows if row.get("normalized_url")}


def write_batch(payload: dict[str, Any]) -> None:
    request("POST", "crawl_batches", payload=payload, prefer="return=minimal")


def source_articles(category: str, config: dict[str, Any], target_date: str) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    for source in config["feeds"]:
        if source.get("type") == "scrape":
            fetched = fetch_10jqka(target_date) if "10jqka" in source["url"] else []
        else:
            fetched = fetch_feed(source, target_date)
        for article in fetched[:MAX_ITEMS_PER_SOURCE]:
            article["category"] = category
            articles.append(article)
    return articles


def enrich(article: dict[str, Any]) -> str:
    content = article.get("content", "")
    if not content:
        return article["title"]
    try:
        return summarize_article(article["title"], content, article.get("lang", "zh"))
    except Exception:
        return content[:180].strip() or article["title"]


def run(target_date: str) -> dict[str, int]:
    batch_id = int(datetime.now(tz=ZoneInfo("Asia/Shanghai")).timestamp() * 1000)
    brief_id = get_or_create_brief(target_date)
    write_batch({
        "id": batch_id,
        "brief_id": brief_id,
        "status": "running",
        "started_at": datetime.now(tz=ZoneInfo("Asia/Shanghai")).isoformat(),
    })

    existing = known_urls()
    inserted_rows: list[dict[str, Any]] = []
    dedup_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    sequence = 0
    source_count = success_count = 0

    for category, config in SOURCES.items():
        for source in config["feeds"]:
            source_count += 1
            try:
                if source.get("type") == "scrape":
                    fetched = fetch_10jqka(target_date) if "10jqka" in source["url"] else []
                else:
                    fetched = fetch_feed(source, target_date)
                success_count += 1
            except Exception as error:  # Each source remains isolated.
                errors.append(f"[{source['name']}] {error}")
                continue

            for article in fetched[:MAX_ITEMS_PER_SOURCE]:
                canonical = normalize_url(article.get("source_url", ""))
                if not canonical or canonical in existing:
                    continue
                existing.add(canonical)
                sequence += 1
                inserted_rows.append({
                    "id": batch_id + sequence,
                    "brief_id": brief_id,
                    "title": article["title"],
                    "summary": enrich(article),
                    "image_url": article.get("image_url", ""),
                    "category": category,
                    "source": source["name"],
                    "source_url": article.get("source_url", ""),
                    "sort_order": sequence,
                })
                dedup_rows.append({
                    "id": batch_id + 100000 + sequence,
                    "normalized_url": canonical,
                    "title_hash": title_hash(article["title"]),
                    "pub_date": article.get("date", target_date),
                })

    if inserted_rows:
        request("POST", "news_items", payload=inserted_rows, prefer="return=minimal")
        request("POST", "crawl_dedup", payload=dedup_rows, prefer="return=minimal")

    write_batch({
        "id": batch_id + 1,
        "brief_id": brief_id,
        "status": "done" if not errors else "partial",
        "total_sources": source_count,
        "success_count": success_count,
        "fail_count": source_count - success_count,
        "new_items": len(inserted_rows),
        "error_log": "\n".join(errors)[:2000],
        "started_at": datetime.now(tz=ZoneInfo("Asia/Shanghai")).isoformat(),
        "finished_at": datetime.now(tz=ZoneInfo("Asia/Shanghai")).isoformat(),
    })
    return {"brief_id": brief_id, "new_items": len(inserted_rows), "failed_sources": source_count - success_count}


if __name__ == "__main__":
    default_date = (datetime.now(tz=ZoneInfo("Asia/Shanghai")) - timedelta(days=1)).date().isoformat()
    target = os.environ.get("NEWS_DATE", default_date)
    print(run(target))
