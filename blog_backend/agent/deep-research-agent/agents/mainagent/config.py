"""
配置管理模块。

从环境变量中读取并校验 agent 运行所需的配置。
所有的 env 变量统一在这里处理，不散落在其他模块里。
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """应用配置，所有可调参数集中管理。

    字段说明：
        model: 模型名称（如 gpt-4o、deepseek-chat）
        api_key: API 密钥
        base_url: API 地址（OpenAI 官方或兼容地址）
        agent_root: 虚拟文件系统的根目录
        recursion_limit: LangGraph 最大递归深度（防跑飞）
        max_concurrent_research_units: 并行研究子 agent 数量上限
        max_researcher_iterations: 研究子 agent 最大迭代轮次
        memory_enabled: 是否启用记忆系统
        memory_storage_path: 记忆存储路径
    """
    model: str
    api_key: str
    base_url: str | None = None
    agent_root: str = "/Users/zhuyq/blog/blog_backend/agent/deep-research-agent/"
    recursion_limit: int = 1000
    max_concurrent_research_units: int = 10
    max_researcher_iterations: int = 10
    memory_enabled: bool = True
    memory_storage_path: str = "./memory_data"

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量构造配置，缺失必填项时直接报错。"""
        errors = []

        model = os.getenv("OPENAI_MODEL", "")
        if not model:
            errors.append("OPENAI_MODEL 未设置")

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            errors.append("OPENAI_API_KEY 未设置")

        if errors:
            raise ValueError(
                "配置缺失:\n  " + "\n  ".join(errors)
            )

        return cls(
            model=model,
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL"),
            agent_root=os.getenv("AGENT_ROOT", "./data"),
            recursion_limit=int(os.getenv("RECURSION_LIMIT", "150")),
            max_concurrent_research_units=int(os.getenv("MAX_CONCURRENT_RESEARCH_UNITS", "3")),
            max_researcher_iterations=int(os.getenv("MAX_RESEARCHER_ITERATIONS", "3")),
            memory_enabled=os.getenv("MEMORY_ENABLED", "true").lower() == "true",
            memory_storage_path=os.getenv("MEMORY_STORAGE_PATH", "./memory_data"),
        )
