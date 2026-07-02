#!/usr/bin/env python3
"""
搜索索引构建脚本
合并所有历史新闻数据，生成 static/search-index.json 供前端检索
"""

import json
from pathlib import Path


def main():
    """
    扫描 static/news-*.json 文件，合并为统一搜索索引
    """
    print("=== 构建搜索索引 ===\n")

    static_dir = Path(__file__).parent.parent / "static"
    all_items = []
    seen_ids = set()

    # 收集所有 news-YYYY-MM-DD.json 文件
    news_files = sorted(static_dir.glob("news-*.json"), reverse=True)
    print(f"  找到 {len(news_files)} 个新闻数据文件")

    global_id = 0
    for nf in news_files:
        try:
            items = json.loads(nf.read_text(encoding="utf-8"))
            for item in items:
                global_id += 1
                item["id"] = global_id  # 重新分配全局唯一 ID
                all_items.append(item)
        except Exception as e:
            print(f"  [WARNING] 读取失败 {nf.name}: {e}")

    print(f"  总计 {len(all_items)} 条新闻")

    # 输出搜索索引
    output_file = static_dir / "search-index.json"
    output_file.write_text(
        json.dumps(all_items, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n✅ 搜索索引: {output_file} ({output_file.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
