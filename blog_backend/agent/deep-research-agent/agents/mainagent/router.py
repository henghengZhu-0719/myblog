"""
FastAPI 路由模块。

提供：
- /chat: 流式对话（自动管理 WorkingMemory）
- /working-memory: 工作记忆的 CRUD
"""

import json
from datetime import datetime
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


# ── 请求/响应模型 ─────────────────────────────────


class ChatRequest(BaseModel):
    message: str


class AddMemoryRequest(BaseModel):
    content: str
    importance: float = 0.5


class MemoryResponse(BaseModel):
    id: str
    content: str
    importance: float
    timestamp: str
    memory_type: str


# ── 依赖注入（由 app 启动时设置） ─────────────────


_agent_service = None
_working_memory = None


def setup(agent_service, working_memory):
    global _agent_service, _working_memory
    _agent_service = agent_service
    _working_memory = working_memory


# ── 工具函数 ─────────────────────────────────────

SUBAGENT_TOOLS = {"tavily_search", "think_tool"}


def _infer_agent_type(tool_name: str) -> str:
    """根据工具名称推断调用者：subagent 仅使用搜索和思考工具。"""
    return "subagent" if tool_name in SUBAGENT_TOOLS else "main"


def _enrich_with_memory(user_input: str) -> str:
    """检索工作记忆中与当前问题相关的记忆并注入到用户消息前。"""
    if _working_memory is None:
        return user_input

    items = _working_memory.retrieve(user_input, limit=5)
    if not items:
        return user_input

    lines = [f"[{i}] {m.content}" for i, m in enumerate(items, 1)]
    memory_block = "\n".join(lines)
    return f"[相关记忆]\n{memory_block}\n\n[当前问题]\n{user_input}"


def _save_to_working_memory(content: str):
    """保存内容到工作记忆。"""
    if _working_memory is None:
        return
    from memory.base import MemoryItem

    item = MemoryItem(
        id=str(uuid4()),
        content=content,
        memory_type="working",
        user_id="default",
        timestamp=datetime.now(),
        importance=0.5,
    )
    _working_memory.add(item)


# ── Chat 路由 ────────────────────────────────────


@router.post("/chat")
async def chat(req: ChatRequest):
    """流式对话：自动保存双方对话到工作记忆 + 检索相关记忆后调用 agent。"""
    if _agent_service is None or _agent_service.agent is None:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    # 1. 保存用户输入到工作记忆
    _save_to_working_memory(f"用户: {req.message}")

    # 2. 检索相关记忆并注入
    enriched = _enrich_with_memory(req.message)

    # 3. 流式返回 agent 回复，同时收集完整回复
    async def generate():
        full_reply = ""
        async for event in _agent_service.stream(enriched):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                text = _extract_text(chunk)
                if text:
                    full_reply += text
                    yield text
            elif kind == "on_tool_start":
                tool_name = event["name"]
                tool_input = event["data"].get("input")
                agent_type = event.get("_agent_type", "main")
                yield f"\n\n[工具: {tool_name}]\n输入: {tool_input}\nagent: {agent_type}\n\n"
            elif kind == "on_tool_end":
                tool_name = event["name"]
                agent_type = event.get("_agent_type", "main")
                yield f"\n[工具完成: {tool_name}]\nagent: {agent_type}\n\n"

        # 4. 流式结束后，保存 AI 回复到工作记忆
        if full_reply:
            _save_to_working_memory(f"助手: {full_reply}")

    return StreamingResponse(generate(), media_type="text/plain")


# ── WorkingMemory 路由 ────────────────────────────


@router.get("/working-memory", response_model=list[MemoryResponse])
async def list_memories():
    """获取所有工作记忆。"""
    if _working_memory is None:
        raise HTTPException(status_code=503, detail="工作记忆未启用")

    items = _working_memory.get_all()
    return [
        MemoryResponse(
            id=m.id,
            content=m.content,
            importance=m.importance,
            timestamp=m.timestamp.isoformat(),
            memory_type=m.memory_type,
        )
        for m in items
    ]


@router.post("/working-memory")
async def add_memory(req: AddMemoryRequest):
    """手动添加一条工作记忆。"""
    if _working_memory is None:
        raise HTTPException(status_code=503, detail="工作记忆未启用")

    _save_to_working_memory(req.content)
    return {"status": "ok", "content": req.content}


@router.delete("/working-memory/{memory_id}")
async def delete_memory(memory_id: str):
    """删除指定记忆。"""
    if _working_memory is None:
        raise HTTPException(status_code=503, detail="工作记忆未启用")

    if not _working_memory.has_memory(memory_id):
        raise HTTPException(status_code=404, detail="记忆不存在")

    _working_memory.remove(memory_id)
    return {"status": "deleted", "id": memory_id}


@router.delete("/working-memory")
async def clear_memories():
    """清空所有工作记忆。"""
    if _working_memory is None:
        raise HTTPException(status_code=503, detail="工作记忆未启用")

    _working_memory.clear()
    return {"status": "cleared"}


@router.get("/working-memory/stats")
async def memory_stats():
    """获取工作记忆统计信息。"""
    if _working_memory is None:
        raise HTTPException(status_code=503, detail="工作记忆未启用")

    return _working_memory.get_stats()


# ── text 提取工具（复用 agent.py 的逻辑） ────────


def _extract_text(chunk) -> str:
    content_blocks = getattr(chunk, "content_blocks", None)
    if content_blocks:
        for block in content_blocks:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    return block.get("text", "")
            elif getattr(block, "type", None) == "text":
                return getattr(block, "text", "")
        return ""

    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
    return ""
