from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from typing import AsyncIterator, Tuple, Any, Dict, Optional
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessageChunk
from langchain.agents.structured_output import ToolStrategy
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
import json
from deepagents.backends import FilesystemBackend
from deepagents import create_deep_agent
from datetime import datetime
from agents.research_agent import (
    RESEARCHER_INSTRUCTIONS,
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from agents.research_agent import tavily_search, think_tool
import os
from dotenv import load_dotenv

load_dotenv()


# 初始化模型
API_KEY = os.getenv("ANTHROPIC_API_KEY")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL")

max_concurrent_research_units = 3
max_researcher_iterations = 3
# 当前日期
current_date = datetime.now().strftime("%Y-%m-%d")
# 主Agent的系统提示词
INSTRUCTIONS = (
    RESEARCH_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
    )
)

# 1. 子Agent - 研究助手
research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate research to the sub-agent researcher. Only give this researcher one topic at a time.",
    "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
    "tools": [tavily_search, think_tool],
}

# model and main agent
model = ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL"),
            api_key=API_KEY,
            base_url=BASE_URL,
            )

agent = create_deep_agent(
    model = model,
    tools=[tavily_search, think_tool],
    system_prompt=INSTRUCTIONS,
    subagents=[research_sub_agent],
    backend=FilesystemBackend(root_dir="/Users/zhuyq/blog/blog_backend/agent/研究报告", virtual_mode=True)
)

result = agent.invoke({"messages": [{"role": "user", "content": "你好呀!"}]})

# Print the agent's response
print(result["messages"][-1].content)