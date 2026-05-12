import json
import logging
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# deep-research-agent 目录名带连字符，无法直接 import，需要加到 sys.path
_deep_agent_root = Path(__file__).resolve().parent.parent / "agent" / "deep-research-agent"
if str(_deep_agent_root) not in sys.path:
    sys.path.insert(0, str(_deep_agent_root))

from agents.mainagent.agent import AgentService, _extract_text
from agents.mainagent.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter()

_agent_service: AgentService | None = None


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        config = Settings.from_env()
        _agent_service = AgentService(config)
        _agent_service.init()
        logger.info("Deep Research Agent 初始化完成")
    return _agent_service


class ChatRequest(BaseModel):
    message: str
    user_id: str | int | None = None


@router.post("/chat")
async def chat(request: ChatRequest):
    agent = get_agent_service()

    async def generator():
        async for event in agent.stream(request.message):
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                text = _extract_text(chunk)
                if text:
                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"

            elif kind == "on_tool_start":
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name']})}\n\n"

            elif kind == "on_tool_end":
                yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['name']})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
