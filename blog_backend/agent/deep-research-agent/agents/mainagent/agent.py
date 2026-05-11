"""
Agent 服务接口模块。

对外暴露 AgentService，封装 agent 的初始化和流式调用。
调用方只需要知道 stream()，不需要关心 agent 是如何构造的。
"""

import logging
import threading

from .config import Settings
from .factory import ResearchAgentFactory

logger = logging.getLogger(__name__)


class AgentService:
    """深度研究 agent 的服务封装。

    职责：
        - init(): 初始化 agent（线程安全）
        - stream(): 流式调用 agent，返回事件流
        - debug_run(): 本地调试，打印可读的输出

    使用方式：
        config = Settings.from_env()
        service = AgentService(config)
        service.init()
        async for event in service.stream("用户问题"):
            ...
    """

    def __init__(self, config: Settings):
        self.config = config
        self.agent = None
        self._lock = threading.Lock()

    def init(self):
        """初始化 agent（线程安全，重复调用无害）。"""
        if self.agent is not None:
            return
        with self._lock:
            if self.agent is not None:
                return
            logger.info("正在初始化 agent ...")
            self.agent = ResearchAgentFactory.create(self.config)
            logger.info("agent 初始化完成")

    async def stream(self, user_input: str):
        """流式调用 agent，逐个 yield 事件。

        适用于 FastAPI StreamingResponse 等场景。
        """
        if self.agent is None:
            raise RuntimeError("AgentService 未初始化，请先调用 init()")

        async for event in self.agent.astream_events(
            {"messages": [{"role": "user", "content": user_input}]},
            version="v2",
            config={"recursion_limit": self.config.recursion_limit},
        ):
            yield event

    async def debug_run(self, user_input: str):
        """本地调试用，在终端打印结构化的 AI 回复和工具调用日志。"""
        print(f"用户: {user_input}\n")
        current_mode = None

        async for event in self.stream(user_input):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                text = _extract_text(event["data"]["chunk"])
                if text:
                    if current_mode != "ai":
                        print("\nAI回复：", end="", flush=True)
                        current_mode = "ai"
                    print(text, end="", flush=True)

            elif kind == "on_tool_start":
                tool_name = event["name"]
                tool_input = event["data"].get("input")
                agent_label = event.get("_agent_type", "main")
                print(f"\n\n[{agent_label}] 工具调用：{tool_name}", flush=True)
                if tool_input:
                    print(f"工具输入：{tool_input}", flush=True)
                current_mode = "tool"

            elif kind == "on_tool_end":
                tool_name = event["name"]
                output = event["data"].get("output")
                print(f"\n工具完成：{tool_name}", flush=True)
                current_mode = None

        print("\n")


def _extract_text(chunk) -> str:
    """从 chat model stream chunk 中提取文本内容。

    LangChain 的 chunk 有多种格式（dict / object / list），
    这个函数统一处理，保证拿到纯文本。
    """
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
