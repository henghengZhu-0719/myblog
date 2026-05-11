"""
Agent 工厂模块。

负责把模型、工具、prompt、子 agent 等零件装配成一个完整的 deep agent。
这里是修改 agent 行为的主要入口。
"""

from datetime import datetime

from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent, CompiledSubAgent
from deepagents.backends import FilesystemBackend

from agents.research_agent import (
    tavily_search,
    think_tool,
    RESEARCHER_INSTRUCTIONS,
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from .config import Settings
from agent.rag.pipeline.graph import RagGraph

class ResearchAgentFactory:
    """深度研究 agent 的工厂。

    使用方式：
        config = Settings.from_env()
        agent = ResearchAgentFactory.create(config)
    """

    @staticmethod
    def build_main_prompt(config: Settings) -> str:
        """组装主 agent 的系统提示词。

        将研究工作流 + 子代理委派策略拼成完整的 instructions。
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        return (
            RESEARCH_WORKFLOW_INSTRUCTIONS
            + "\n\n"
            + "=" * 80
            + "\n\n"
            + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
                max_concurrent_research_units=config.max_concurrent_research_units,
                max_researcher_iterations=config.max_researcher_iterations,
            )
            + f"今天是{current_date}"
        )

    @staticmethod
    def build_research_sub_agent(config: Settings) -> dict:
        """构建 research-agent 子 agent 的配置。"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        return {
            "name": "research-agent",
            "description": "Delegate research to the sub-agent researcher. Only give this researcher one topic at a time.",
            "system_prompt": RESEARCHER_INSTRUCTIONS.format(date=current_date),
            "tools": [tavily_search, think_tool],
        }
    
    @staticmethod
    def build_rag_agent(config: Settings):
        """构建 rag-agent 子 agent"""
        rag_graph = RagGraph()._build_graph() # 编译 rag-agent 图
        rag_agent = CompiledSubAgent(
            name="rag-agent",
            description="Delegate research to the sub-agent researcher. Only give this researcher one topic at a time. the sub-agent researcher.",
            runnable=rag_graph
        )

        return rag_agent
    

    @staticmethod
    def create(config: Settings):
        """创建并返回一个完整的 deep agent。"""
        rag_agent = ResearchAgentFactory.build_rag_agent(config)
        return create_deep_agent(
            model=ChatOpenAI(
                model=config.model,
                api_key=config.api_key,
                base_url=config.base_url,
                extra_body={"thinking": {"type": "disabled"}},
            ),
            tools=[tavily_search, think_tool],
            system_prompt=ResearchAgentFactory.build_main_prompt(config),
            subagents=[ResearchAgentFactory.build_research_sub_agent(config), rag_agent],
            backend=FilesystemBackend(
                root_dir=config.agent_root,
                virtual_mode=True,
            ),
        )
