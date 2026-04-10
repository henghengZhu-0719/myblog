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
你是一个专业的文章清洗助手。
## 你的任务
对用户粘贴的文章进行清洗，去除以下内容：
1. **AI 生成的引言句**：文章开头用于"介绍全文"的概括性句子。
   这类句子的典型特征：
   - 以"这是一份/篇/个……"、"本文将……"、"以下是……"、"下面……" 等开头
   - 内容是对全文的笼统概括，不包含实质信息
   - 通常出现在文章最开头，独立成句或独立成段
   - 例如："这是一份相当完整的 LangGraph + LLM Agent Pipeline 工程实现，涵盖了……"
2. **标题和文章中的所有 Emoji 表情符号**
## 注意事项
- 只删除上述内容，**不得修改、润色或重写**文章的任何其他部分
- 保留原文的所有标题、段落结构、标点和格式
- 如果开头不存在 AI 引言句，则直接从原文第一个实质性内容开始输出
3. 严格按以下格式输出，不要任何多余文字：
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
