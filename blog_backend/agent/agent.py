from langchain_anthropic import ChatAnthropic
from deepagents.backends import FilesystemBackend
from deepagents import create_deep_agent
from datetime import datetime
from agent.agents.research_agent import (
    RESEARCHER_INSTRUCTIONS,
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from agent.agents.research_agent import tavily_search, think_tool

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

max_concurrent_research_units = 3
max_researcher_iterations = 3


class AgentService:
    def __init__(self):
        self.agent = None

    def init(self):
        """在 FastAPI startup 时调用"""
        if self.agent is not None:
            return

        current_date = datetime.now().strftime("%Y-%m-%d")

        instructions = (
            RESEARCH_WORKFLOW_INSTRUCTIONS
            + "\n\n"
            + "=" * 80
            + "\n\n"
            + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
                max_concurrent_research_units=max_concurrent_research_units,
                max_researcher_iterations=max_researcher_iterations,
            )
            + f"今天是{current_date}"
        )

        research_sub_agent = {
            "name": "research-agent",
            "description": "Delegate research to the sub-agent researcher. Only give this researcher one topic at a time.",
            "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
            "tools": [tavily_search, think_tool],
        }

        model = ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
        )

        self.agent = create_deep_agent(
            model=model,
            tools=[tavily_search, think_tool],
            system_prompt=instructions,
            subagents=[research_sub_agent],
            backend=FilesystemBackend(
                root_dir=os.getenv("AGENT_ROOT", "./data"),  # ✅ 改成可配置
                virtual_mode=True,
            ),
        )

    async def stream(self, user_input: str):
        """用于 FastAPI StreamingResponse"""
        if self.agent is None:
            raise RuntimeError(
                "AgentService 未初始化，请先调用 init() 方法 "
                "(或检查服务启动日志中是否有初始化失败的记录)"
            )

        async for event in self.agent.astream_events(
            {"messages": [{"role": "user", "content": user_input}]},
            version="v2",
            config={"recursion_limit": 1000},
        ):
            yield event

    async def debug_run(self, user_input: str):
        """本地调试用（保留你原来的打印逻辑）"""
        print(f"用户: {user_input}\n")

        current_mode = None

        async for event in self.stream(user_input):
            kind = event["event"]

            # AI 流式回复
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
                    if current_mode != "ai":
                        prefix = (
                            "\n\nAI回复："
                            if current_mode == "tool"
                            else "\nAI回复："
                        )
                        print(prefix, end="", flush=True)
                        current_mode = "ai"
                    print(text, end="", flush=True)

            # 工具开始
            elif kind == "on_tool_start":
                tool_name = event["name"]
                tool_input = event["data"].get("input")

                print(f"\n\n工具调用：{tool_name}", flush=True)
                if tool_input:
                    print(f"工具输入：{tool_input}", flush=True)

                current_mode = "tool"

            # 工具结束
            elif kind == "on_tool_end":
                tool_name = event["name"]
                output = event["data"].get("output")

                print(f"\n工具输出：", end="", flush=True)
                if output is not None:
                    print(output, end="", flush=True)

                print(f"\n工具完成：{tool_name}", flush=True)

                current_mode = None

        print("\n")


# =========================
# 本地运行入口（调试用）
# =========================
if __name__ == "__main__":
    import asyncio

    service = AgentService()
    service.init()

    asyncio.run(
        service.debug_run(
            "帮我总结一下江西省科学院科技战略研究所的日常性工作是什么？因为我要应聘综合管理类岗位"
        )
    )