from decimal import Context
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
import json
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver

# 初始化模型
API_KEY = "sk-cp-tP-n3FkUJPYRQqZb_w5nMIZYjQHwwsiEjQg-zldzQOfNQfYZKT8qnkxxu2EdBG2ORDs2yMcd-XNjxKRWxxbW0CwsVEnCzf5aHUfx4qIMYwEgCCJAzn1NmlQ"
BASE_URL = "https://api.minimaxi.com/anthropic"

class Agent:
    def __init__(self, model_name="MiniMax-M2.7"):
        self.chat_model = ChatAnthropic(
            model=model_name,
            api_key=API_KEY,
            base_url=BASE_URL,
        )
        # 引入记忆系统
        self.checkpointer = InMemorySaver()
        # 构建agent
        self.agent = create_agent(
            model=self.chat_model,
            tools=[],
            checkpointer=self.checkpointer,
        )
    
    async def astream_chat(self, message: str, user_id: str = "zhuyq"):
        """流式对话生成器"""
        if not self.chat_model:
            raise Exception("AI 模型未正确初始化")
        config = {"congigurable": {"thread_id":"user_id"}}
        async for chunk in self.agent.astream(
            input=[{"role": "user", "content": message}],
            temperature=0.1,
            config = config,
            context = Context(user_id = user_id)
        ):
            chunk_text = ""
            if isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        chunk_text += block.get("text", "")
                    elif hasattr(block, "type") and block.type == "text":
                        chunk_text += getattr(block, "text", "")
            else:
                chunk_text = str(chunk.content)
            
            if chunk_text:
                yield chunk_text