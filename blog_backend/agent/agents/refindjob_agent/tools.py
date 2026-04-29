"""Research Tools.

This module provides search and content processing utilities for the research agent,
using Tavily for URL discovery and fetching full webpage content.
"""

import httpx
from langchain_core.tools import InjectedToolArg, tool
from markdownify import markdownify
from tavily import TavilyClient
from typing_extensions import Annotated, Literal
import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """获取网页内容并将其转换为 Markdown 格式。

    Args:
        url: 地址栏
        timeout: 请求超时时间（秒）；

    Returns:
        页面内容作为 Markdown 格式
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return markdownify(response.text)
    except Exception as e:
        return f"Error fetching content from {url}: {str(e)}"


@tool(parse_docstring=True)
def job_tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """根据给定查询在网络上搜索信息。

        使用 Tavily 发现相关网址，然后抓取并以 Markdown 格式返回完整网页内容。

        Args:
            query: 要执行的搜索查询
            max_results: 返回的最大结果数量（默认：1）
            topic: 主题过滤，可选 'general'（通用）、'news'（新闻）或 'finance'（金融）（默认：'general'）

        Returns:
            包含完整网页内容的格式化搜索结果
    """
    # Use Tavily to discover URLs
    search_results = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
    )

    # Fetch full content for each URL
    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]

        # Fetch webpage content
        content = fetch_webpage_content(url)

        result_text = f"""## {title}
**URL:** {url}

{content}

---
"""
        result_texts.append(result_text)

    # Format final response
    response = f"""🔍 Found {len(result_texts)} result(s) for '{query}':

{chr(10).join(result_texts)}"""

    return response


@tool(parse_docstring=True)
def job_think_tool(reflection: str) -> str:
    """用于对研究进展和决策进行战略性反思的工具。

        在每次搜索后使用此工具，系统性地分析结果并规划下一步。
        这会在研究流程中创建一个有意识的暂停，用于提升决策质量。

        使用场景：
        - 收到搜索结果后：我找到了哪些关键信息？
        - 决定下一步之前：我是否已有足够信息来全面回答？
        - 评估研究缺口时：我还缺少哪些具体信息？
        - 结束研究之前：现在是否可以给出完整答案？

        反思应涵盖：
        1. 当前发现分析 —— 我收集到了哪些具体信息？
        2. 缺口评估 —— 还缺少哪些关键信息？
        3. 质量评估 —— 是否有足够证据/示例来形成高质量回答？
        4. 策略决策 —— 应该继续搜索，还是直接给出答案？

        Args:
            reflection: 你对研究进展、发现、缺口和下一步的详细反思

        Returns:
            确认该反思已被记录，用于辅助决策
    """
    return f"已记录反思: {reflection}"
