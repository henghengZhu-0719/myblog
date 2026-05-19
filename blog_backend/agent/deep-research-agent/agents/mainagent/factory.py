"""
Agent 工厂模块。

负责把模型、工具、prompt、子 agent 等零件装配成一个完整的 deep agent。
这里是修改 agent 行为的主要入口。
"""

from datetime import datetime
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent, CompiledSubAgent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

from agents.research_agent import (
    tavily_search,
    think_tool,
    RESEARCHER_INSTRUCTIONS,
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    RAG_AGENT_INSTRUCTIONS,
)
from .config import Settings
from agent.rag.pipeline.graph import RagGraph

# 全局缓存，避免重复创建重量级的 RagGraph 实例
_rag_graph: RagGraph | None = None

def _get_rag_graph() -> RagGraph:
    global _rag_graph
    if _rag_graph is None:
        _rag_graph = RagGraph()
    return _rag_graph


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
            + "\n\n"
            + f"\n\n今天是{current_date}"
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
    
    # @staticmethod
    # def build_rag_agent(config: Settings):
    #     """构建 rag-agent 子 agent"""
    #     rag_graph = _get_rag_graph().graph  # 编译 rag-agent 图
    #     rag_agent = CompiledSubAgent(
    #         name="rag-agent",
    #         description="Query the local knowledge base for questions about the blog's technical content. Use this when the user asks about concepts, technologies, or topics that might be covered in the blog.",
    #         runnable=rag_graph
    #     )

    #     return rag_agent
    
    @traceable
    def create(config: Settings):
        """创建并返回一个完整的 deep agent。"""
        # rag_agent = ResearchAgentFactory.build_rag_agent(config)
        return create_deep_agent(
            model=ChatOpenAI(
                model=config.model,
                api_key=config.api_key,
                base_url=config.base_url,
                extra_body={"thinking": {"type": "disabled"}},
            ),
            tools=[tavily_search, think_tool],
            system_prompt=ResearchAgentFactory.build_main_prompt(config),
            subagents=[ResearchAgentFactory.build_research_sub_agent(config)],
            backend=FilesystemBackend(
                root_dir=config.agent_root
            ),
            skills=["/Users/zhuyq/blog/blog_backend/agent/deep-research-agent/skills/rag-knowledge-base"],
        )
