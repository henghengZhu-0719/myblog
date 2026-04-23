
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from tools.web_search import get_mcp_tools
from tools.crawl_html import crawl_html
import asyncio
# 初始化模型
API_KEY = "sk-cp-tP-n3FkUJPYRQqZb_w5nMIZYjQHwwsiEjQg-zldzQOfNQfYZKT8qnkxxu2EdBG2ORDs2yMcd-XNjxKRWxxbW0CwsVEnCzf5aHUfx4qIMYwEgCCJAzn1NmlQ"
BASE_URL = "https://api.minimaxi.com/anthropic"

chat_model = ChatAnthropic(
    model = "MiniMax-M2.7",
    api_key = API_KEY,
    base_url = BASE_URL,
)

# tools
web_search_tools = asyncio.run(get_mcp_tools())

# agent
agent = create_agent(
    model=chat_model,
    tools=[*web_search_tools, crawl_html],
)
# prompt
system_prompt = """
你是一个专业的网站解析助手。

## 任务说明
根据用户提出的问题，使用 web_search 工具搜索用户所提到的目标网站，提取关键信息后，以标准 JSON 格式输出结果。

## 执行步骤
1. 分析用户问题，识别需要搜索的目标网站或关键词
2. 调用 web_search 工具进行检索（可多次调用以获取更全面的信息）
3. 对搜索结果进行整理和去重
4. 按照以下格式输出最终结果

## 输出格式
以 JSON 格式输出，结构如下：
```json
{
  "query": "用户的原始问题",
  "results": [
    {
      "name": "网站名称",
      "url": "网站地址",
      "description": "网站简介",
      "category": "网站分类"
    }
  ],
  "total": "结果总数",
  "summary": "整体总结"
}

"""

# run
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "请帮我找到南昌相关的招聘网站"}
]
msg = asyncio.run(agent.ainvoke({"messages": messages}))
print(msg["messages"][-1].content[1])       
