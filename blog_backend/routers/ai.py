from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from agent.agent import AgentService

router = APIRouter()
agent_service = AgentService()


class ChatRequest(BaseModel):
    message: str
    user_id: int | str | None = None

@router.post("/chat")
async def chat(request: ChatRequest):
    try:

        async def generator():
            async for event in agent_service.stream(request.message):
                kind = event.get("event")

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    text = ""

                    content_blocks = getattr(chunk, "content_blocks", None)
                    if content_blocks:
                        for block in content_blocks:
                            block_type = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
                            if block_type == "text":
                                text = block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "")
                    else:
                        content = getattr(chunk, "content", None)
                        if content and isinstance(content, str):
                            text = content
                        elif content and isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text = block.get("text", "")

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
            }
        )

    except Exception as e:
        return {"error": str(e)}