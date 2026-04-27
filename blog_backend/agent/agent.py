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
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver

# 初始化模型
API_KEY = "sk-e146a0bd7f344bc58f61f5c3ee9b7ab7"
BASE_URL = "https://api.deepseek.com/anthropic"

@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str

class Agent:
    def __init__(self, model_name="DeepSeek-V4-Pro"):
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
            context_schema=Context,
            checkpointer=self.checkpointer,
        )
    
    # async def astream_chat(self, message: str, user_id: str | None = None):
    #     """流式对话生成器"""
    #     if not self.chat_model:
    #         raise Exception("AI 模型未正确初始化")
    #     config = {
    #         "configurable": {
    #             "thread_id": user_id or "default"
    #         }
    #     }
    #     async for chunk in self.agent.astream(
    #         input={"messages": [{"role": "user", "content": message}]}, 
    #         temperature=0.1,
    #         config = config,
    #         context = Context(user_id = user_id)
    #     ):
    #         chunk_text = ""
    #         if isinstance(chunk.content, list):
    #             for block in chunk.content:
    #                 if isinstance(block, dict) and block.get("type") == "text":
    #                     chunk_text += block.get("text", "")
    #                 elif hasattr(block, "type") and block.type == "text":
    #                     chunk_text += getattr(block, "text", "")
    #         else:
    #             chunk_text = str(chunk.content)
            
    #         if chunk_text:
    #             yield chunk_text

    
    async def astream_chat(
        self, message: str, user_id: str = None
    ) -> AsyncIterator[Tuple[str, Dict[str, Any]]]:
        """
        使用 agent.astream()
        """
        run_config = {"configurable": {"thread_id": user_id or "default"}} if user_id else {}

        async for chunk in self.agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            config=run_config,
            stream_mode="messages",
            version="v2",
        ):
            if not isinstance(chunk, dict):
                continue

            chunk_type = chunk.get("type")
            if chunk_type != "messages":
                continue

            data = chunk.get("data")
            if not isinstance(data, tuple) or len(data) != 2:
                continue

            token, metadata = data

            if token is None:
                continue

            if isinstance(token, AIMessageChunk):
                content = token.content
            elif hasattr(token, "content"):
                content = token.content
            else:
                continue

            if isinstance(content, str) and content:
                yield content, {"step": metadata, "thread_id": user_id or "default"}
            elif isinstance(content, list):
                for block in content:
                    text = None
                    if isinstance(block, dict):
                        text = block.get("text", "")
                    elif hasattr(block, "text"):
                        text = block.text
                    if text:
                        yield text, {"step": metadata, "thread_id": user_id or "default"}
