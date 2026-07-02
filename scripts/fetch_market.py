#!/usr/bin/env python3
"""
市场行情抓取脚本
A股：新浪财经免费 API (hq.sinajs.cn)
美股/港股：Yahoo Finance API（仅在 GitHub Actions 海外服务器可用）
输出：static/market-data.json
"""

import json
import re
from datetime import datetime
from pathlib import Path

import requests


# A股指数 — 新浪财经 API
A_SHARE_INDICES = [
    {"symbol": "s_sh000001", "name": "上证指数"},
    {"symbol": "s_sz399001", "name": "深证成指"},
    {"symbol": "s_sz399006", "name": "创业板指"},
]

# 美股/港股 — Yahoo Finance API
OVERSEAS_INDICES = [
    {"symbol": "^DJI", "name": "道琼斯"},
    {"symbol": "^IXIC", "name": "纳斯达克"},
    {"symbol": "^GSPC", "name": "标普500"},
    {"symbol": "^HSI", "name": "恒生指数"},
]


def fetch_from_sina(symbol: str) -> dict | None:
    """
    从新浪财经免费 API 获取 A 股指数行情

    新浪返回格式示例：
    var hq_str_s_sh000001="上证指数,3580.12,5.23,0.15,2345678,23456789";
    字段：名称,当前价,涨跌额,涨跌幅(%),成交量(手),成交额(万)

    Args:
        symbol: 新浪代码，如 "s_sh000001"

    Returns:
        {"price": ..., "change": ...} 或 None
    """
    try:
        url = f"https://hq.sinajs.cn/list={symbol}"
        headers = {
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "gbk"

        if resp.status_code != 200:
            return None

        # 解析返回数据
        match = re.search(r'"(.+)"', resp.text)
        if not match:
            return None

        fields = match.group(1).split(",")
        if len(fields) >= 4:
            price = float(fields[1])
            change_pct = float(fields[3])
            return {
                "price": round(price, 2),
                "change": round(change_pct, 2),
            }
    except Exception as e:
        print(f"  [WARNING] 新浪请求失败 ({symbol}): {e}")

    return None


def fetch_from_yahoo(symbol: str) -> dict | None:
    """
    从 Yahoo Finance 获取美股/港股行情数据
    注：仅在海外服务器（如 GitHub Actions）可用

    Args:
        symbol: Yahoo 代码，如 "^DJI"

    Returns:
        {"price": ..., "change": ...} 或 None
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": "1d", "range": "2d"}
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        prev_close = meta.get("chartPreviousClose", 0)
        current = meta.get("regularMarketPrice", 0)

        if prev_close and current:
            change_pct = ((current - prev_close) / prev_close) * 100
            return {
                "price": round(current, 2),
                "change": round(change_pct, 2),
            }
    except Exception as e:
        print(f"  [WARNING] Yahoo 请求失败 ({symbol}): {e}")

    return None


def fetch_market_data() -> dict:
    """
    抓取所有指数的行情数据

    Returns:
        {"indices": [...], "updated": "..."}
    """
    print("=== 市场行情抓取 ===\n")
    indices = []

    # A股：新浪财经 API
    print("【A股 - 新浪财经】")
    for idx_config in A_SHARE_INDICES:
        print(f"  抓取: {idx_config['name']} ({idx_config['symbol']})")
        result = fetch_from_sina(idx_config["symbol"])

        if result:
            indices.append({
                "name": idx_config["name"],
                "symbol": idx_config["symbol"],
                "price": result["price"],
                "change": result["change"],
            })
            print(f"    ✓ {result['price']} ({result['change']:+.2f}%)")
        else:
            indices.append({
                "name": idx_config["name"],
                "symbol": idx_config["symbol"],
                "price": None,
                "change": 0,
            })
            print(f"    ✗ 获取失败")

    # 美股/港股：Yahoo Finance
    print("\n【美股/港股 - Yahoo Finance】")
    for idx_config in OVERSEAS_INDICES:
        print(f"  抓取: {idx_config['name']} ({idx_config['symbol']})")
        result = fetch_from_yahoo(idx_config["symbol"])

        if result:
            indices.append({
                "name": idx_config["name"],
                "symbol": idx_config["symbol"],
                "price": result["price"],
                "change": result["change"],
            })
            print(f"    ✓ {result['price']} ({result['change']:+.2f}%)")
        else:
            indices.append({
                "name": idx_config["name"],
                "symbol": idx_config["symbol"],
                "price": None,
                "change": 0,
            })
            print(f"    ✗ 获取失败（可能需要海外服务器）")

    return {
        "indices": indices,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def main():
    data = fetch_market_data()

    output_file = Path(__file__).parent.parent / "static" / "market-data.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n✅ 输出文件: {output_file}")


if __name__ == "__main__":
    main()
