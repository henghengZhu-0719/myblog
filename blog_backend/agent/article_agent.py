import re
import json
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
import asyncio


import re
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

API_KEY = "sk-cp-tP-n3FkUJPYRQqZb_w5nMIZYjQHwwsiEjQg-zldzQOfNQfYZKT8qnkxxu2EdBG2ORDs2yMcd-XNjxKRWxxbW0CwsVEnCzf5aHUfx4qIMYwEgCCJAzn1NmlQ"

BASE_URL = "https://api.minimaxi.com/anthropic"

chat_model = ChatAnthropic(
    model="MiniMax-M2.7",
    api_key=API_KEY,
    base_url=BASE_URL
)

class ArticleResult(BaseModel):
    title: str
    content: str

PROMPT = """
你是一个专业的文章助手。请去除标题和文章中的所有 Emoji 表情，其余内容保持不变。
严格按以下格式输出，不要任何多余文字：
TITLE: 处理后的标题
CONTENT: 处理后的文章内容
"""

async def check_article(article: str, title: str) -> ArticleResult:
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": f"标题：{title}\n文章：{article}"},
    ]
    response = await chat_model.ainvoke(messages)
    text = response.content[1]["text"]

    # 解析 TITLE 和 CONTENT
    title_match = re.search(r"TITLE:\s*(.+)", text)
    content_match = re.search(r"CONTENT:\s*([\s\S]+)", text)

    clean_title = title_match.group(1).strip() if title_match else title
    clean_content = content_match.group(1).strip() if content_match else article

    return ArticleResult(title=clean_title, content=clean_content)
