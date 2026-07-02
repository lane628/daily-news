"""
DeepSeek API 封装
用于生成新闻摘要
"""

import os
from openai import OpenAI


def get_client():
    """获取 DeepSeek API 客户端"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("环境变量 DEEPSEEK_API_KEY 未设置")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )


def summarize_article(title: str, content: str, lang: str = "zh") -> str:
    """
    使用 DeepSeek 生成文章摘要

    Args:
        title: 文章标题
        content: 文章内容（前 2000 字）
        lang: 原文语言 ('zh' 或 'en')

    Returns:
        2-3 句中文摘要
    """
    client = get_client()

    if lang == "en":
        prompt = f"""请将以下英文新闻翻译并概括为2-3句中文摘要，保留关键信息：

标题：{title}
内容：{content[:2000]}

要求：
- 输出纯中文摘要，2-3句话
- 保留关键数据和人名
- 不要加任何前缀或标记"""
    else:
        prompt = f"""请将以下新闻概括为2-3句中文摘要：

标题：{title}
内容：{content[:2000]}

要求：
- 2-3句话概括核心内容
- 保留关键数据和人名
- 不要加任何前缀或标记"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一位专业的新闻编辑，擅长提炼新闻要点。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [WARNING] 摘要生成失败: {e}")
        return content[:150] + "..."


def batch_summarize(articles: list) -> list:
    """
    批量生成摘要

    Args:
        articles: [{"title": ..., "content": ..., "lang": ...}, ...]

    Returns:
        带 summary 字段的文章列表
    """
    for article in articles:
        if not article.get("summary"):
            article["summary"] = summarize_article(
                article["title"],
                article.get("content", ""),
                article.get("lang", "zh")
            )
    return articles
