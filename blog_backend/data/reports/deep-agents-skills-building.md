# Deep Agents Skills 构建完整指南

## 一、概述

Skills（技能）是 Deep Agents 框架中用于扩展 Agent 能力的核心机制。它们是以目录组织的可复用能力包，包含指令、脚本和资源文件，使 Agent 能够通过"渐进式披露（Progressive Disclosure）"模式按需加载专业技能，而非将所有上下文一次性注入系统提示词中[1][2]。

Deep Agents 的 Skills 机制遵循 [Agent Skills 开放规范](https://agentskills.io/specification)，与 Anthropic Claude Skills、Microsoft Agent Framework 等系统保持兼容，确保了技能的跨平台可移植性[2][3]。

## 二、Skill 文件结构与规范

### 2.1 基本目录结构

一个标准的 Skill 是一个包含 `SKILL.md` 文件的目录，可选包含以下子目录[2][3]：

```
skills/
├── skill-name/
│   ├── SKILL.md                    # 必需 — 包含 frontmatter 元数据和指令
│   ├── scripts/                    # 可选 — 可执行脚本（.py, .js, .sh 等）
│   │   └── script.py
│   ├── references/                 # 可选 — 按需加载的参考文档
│   │   └── reference.md
│   └── assets/                     # 可选 — 模板和静态资源
│       └── template.md
```

### 2.2 SKILL.md 格式

`SKILL.md` 文件必须包含 YAML Frontmatter 元数据，后接 Markdown 格式的指令内容[2][3]：

```yaml
---
name: skill-name
description: 技能描述，当任务匹配时 Agent 会根据此描述决定是否使用该技能
license: MIT
compatibility: 环境要求描述
metadata:
  author: author-name
  version: "1.0"
allowed-tools: fetch_url  # 可选，预先批准的工具列表
---
```

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | 是 | 最多 64 字符。仅限小写字母、数字和连字符。必须与父目录名一致 |
| `description` | 是 | 技能功能和适用场景。最多 1024 字符。应包含帮助 Agent 识别匹配任务的关键词 |
| `license` | 否 | 许可证名称或引用 |
| `compatibility` | 否 | 环境要求（产品、系统包、网络访问等），最多 500 字符 |
| `metadata` | 否 | 额外的键值对元数据 |
| `allowed-tools` | 否 | 空格分隔的预批准工具列表，实验性功能 |

Frontmatter 之后的内容为技能指令主体，包括分步指导、输入输出示例、常见边界情况等。建议 `SKILL.md` 控制在 500 行以内，详细参考材料放在独立文件中[2]。

## 三、渐进式披露机制

渐进式披露是 Skills 系统的核心设计模式，分为四个阶段[1][2][3]：

### 3.1 广告（Advertise）

每个 Skill 的名称和描述（约 100 tokens）在 Agent 启动时被注入到系统提示词中。Agent 通过这份技能清单知道当前有哪些能力可用。

```
## Skills System
You have access to specialized capabilities defined in Skills.

**Available Skills:**
- **langgraph-docs**: Use this skill for requests related to LangGraph...
  → Read `/skills/langgraph-docs/SKILL.md` for full instructions.
```

### 3.2 加载（Load）

当用户请求与某个技能的描述匹配时，Agent 调用 `read_file` 工具读取完整的 `SKILL.md` 文件获取详细指令。建议 SKILL.md 控制在 5000 tokens 以内[1][2]。

### 3.3 读取资源（Read Resources）

Agent 按需读取 `references/` 和 `assets/` 目录中的补充文件（参考文档、模板等）。

### 3.4 执行脚本（Run Scripts）

Agent 调用脚本目录中的可执行文件完成具体操作。在 Deep Agents 中，脚本执行需要沙箱（Sandbox）环境的支持[1]。

这种设计有效优化了上下文窗口的使用——Agent 始终只加载当前任务所需的信息，防止 Token 溢出。

## 四、在 Deep Agents 中集成 Skills

### 4.1 官方 SDK 方式（推荐）

从 Deep Agents 官方 SDK 开始，直接通过 `skills` 参数传入技能目录路径即可[1]：

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    skills=["/skills/"],  # 技能目录路径
)
```

支持三种 Backend 存储方式[1]：

- **StateBackend（默认）**：通过 `invoke(files={...})` 提供技能文件数据
- **StoreBackend**：通过持久化存储管理技能文件
- **FilesystemBackend**：从磁盘加载技能文件

### 4.2 技能源优先级

当多个技能源包含同名技能时，列表中靠后的源优先级更高（最后加载的获胜）[1]：

```python
# 如果两个源都包含名为 "web-search" 的技能，
# /skills/project/ 中的版本会胜出
agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    skills=["/skills/user/", "/skills/project/"],
)
```

### 4.3 子代理的 Skills 配置

- **通用子代理（General-purpose subagent）**：自动继承主 Agent 的 Skills 配置
- **自定义子代理（Custom subagent）**：不继承主 Agent 的 Skills，需要单独配置 `skills` 参数。技能状态完全隔离——主 Agent 的技能对子代理不可见，反之亦然[1]

```python
research_subagent = {
    "name": "researcher",
    "description": "Research assistant with specialized skills",
    "system_prompt": "You are a researcher.",
    "tools": [web_search],
    "skills": ["/skills/research/"],  # 子代理专属技能
}

agent = create_deep_agent(
    model="google_genai:gemini-3.1-pro-preview",
    skills=["/skills/main/"],          # 主 Agent 技能
    subagents=[research_subagent],
)
```

## 五、手动构建 Skills 集成方案

如果 Deep Agents SDK 尚未直接提供内置的 Skills 支持接口（如早期版本），可以通过以下方式手动构建集成方案[3]：

### 5.1 SkillRegistry 中间件

实现一个 `SkillRegistry` 类来管理技能的发现和注入[3]：

```python
class SkillRegistry:
    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self.skills: List[SkillMetadata] = []
        self._load_skills()
        
    def _load_skills(self):
        # 扫描目录，解析每个 SKILL.md 的 Frontmatter
        for skill_dir in self.skills_dir.iterdir():
            skill_md_path = skill_dir / "SKILL.md"
            if skill_md_path.exists():
                metadata = self._parse_frontmatter(skill_md_path)
                if metadata:
                    self.skills.append(metadata)
    
    def get_system_prompt_addition(self) -> str:
        # 构建动态的技能菜单注入到 System Prompt 中
        lines = ["\n\n## Skills System"]
        for skill in self.skills:
            lines.append(f"- **{skill.name}**: {skill.description}")
            lines.append(f"  -> Read `{skill.path}` for full instructions.")
        return "\n".join(lines)
```

### 5.2 基于 @tool 的脚本封装

将技能关联的脚本封装为标准的 LangChain Tool[3]：

```python
from langchain_core.tools import tool

@tool
def pdf_convert_to_images(pdf_path: str, output_dir: str) -> str:
    """
    Converts pages of a PDF file into PNG images.
    Useful for visual inspection or when text extraction fails.
    """
    # 实现细节
    return f"Successfully converted PDF pages to images in {output_dir}"
```

### 5.3 基于 CompiledSubAgent 的能力隔离

采用 `CompiledSubAgent` 封装技能能力，实现子代理的隔离与专业化[3]：

```python
from deepagents import create_deep_agent, CompiledSubAgent

# 构建 PDF 子代理
pdf_graph = create_deep_agent(
    model=model,
    tools=pdf_tools,
    system_prompt=final_system_prompt,
)

pdf_subagent = CompiledSubAgent(
    name="pdf_specialist",
    description="A specialist agent for PDF operations.",
    runnable=pdf_graph
)
```

## 六、Skills 在沙箱环境中的脚本执行

当技能包含可执行脚本时，Agent 需要访问 Shell 环境来运行它们。只有沙箱后端（Sandbox Backend）提供此能力[1]。

推荐使用 `CompositeBackend` 将技能文件存储在 `StoreBackend` 中持久化，同时使用沙箱作为默认后端执行代码。还需通过自定义中间件将技能文件同步到沙箱文件系统中[1]：

```python
class SkillSandboxSyncMiddleware(AgentMiddleware):
    """在每个 Agent 运行前将技能文件从存储复制到沙箱"""
    async def abefore_agent(self, state, runtime):
        store = runtime.store
        files = []
        for item in await store.asearch(SKILLS_SHARED_NAMESPACE):
            key = str(item.key)
            normalized = key if key.startswith("/") else f"/{key}"
            files.append((f"/skills{normalized}", item.value["content"].encode()))
        if files:
            await self.backend.aupload_files(files)
```

## 七、Skills vs Memory vs Tools

| 特性 | Skills | Memory (AGENTS.md) | Tools |
|------|--------|-------------------|-------|
| **目的** | 按需发现的专业能力 | 始终加载的持久上下文 | 单一功能的原子操作 |
| **加载方式** | 渐进式披露，按需读取 | 启动时注入系统提示词 | 注册为可调用函数 |
| **格式** | 目录结构（SKILL.md + 资源） | 纯 Markdown 文件 | 函数/方法 |
| **适用场景** | 任务特定、可能大量的指令 | 始终相关的上下文（项目约定、偏好） | 简单、频繁使用的操作 |
| **Token 开销** | 低（仅广告阶段消耗） | 固定消耗 | 取决于工具描述长度 |

## 八、最佳实践与安全建议

### 8.1 编写 Skills 的最佳实践

1. **描述要清晰具体**：Agent 仅凭 `description` 字段决定是否使用某个技能，详细的描述有助于 Agent 做出正确的匹配决策[1]
2. **保持 SKILL.md 精简**：将详细参考材料放在独立文件中，主文件控制在 500 行以内[2]
3. **使用版本控制**：通过 `metadata.version` 字段跟踪技能版本，便于维护和更新[2]
4. **声明环境依赖**：在 `compatibility` 字段中明确技能的运行环境要求[2]

### 8.2 安全建议

1. **审查后再部署**：阅读所有技能内容（SKILL.md、脚本和资源）后再部署[2]
2. **来源可信**：仅从受信任的作者或经过审查的内部贡献者处安装技能[2]
3. **沙箱执行**：在隔离环境中运行包含可执行脚本的技能，限制文件系统、网络和系统级访问[1][2]
4. **审计日志**：记录哪些技能被加载、哪些资源被读取、哪些脚本被执行，以便追踪 Agent 行为[2]

## 九、总结

Deep Agents 的 Skills 机制通过渐进式披露、文件即配置的设计模式，成功解决了传统 Agent 在工具扩展性与上下文窗口限制之间的矛盾。开发者可以通过编写标准化的 Markdown 文件来定义技能，Agent 则像人类学习新技能一样，通过阅读文档动态掌握新工具的使用方法。

推荐的使用路径是：先通过 Deep Agents 官方 SDK 的 `skills` 参数直接集成，再根据具体需求（如子代理隔离、沙箱执行、动态资源等）进行深度定制。对于官方 SDK 尚未覆盖的场景，可以采用 SkillRegistry + @tool + CompiledSubAgent 的组合方案手动构建。

---

### Sources

[1] LangChain Docs - Deep Agents Skills: https://docs.langchain.com/oss/python/deepagents/skills
[2] Microsoft Learn - Agent Skills: https://learn.microsoft.com/en-us/agent-framework/agents/skills
[3] LangChain Deep Agents 集成 Claude Skills 技能指南 - ApFramework: https://apframework.com/blog/essay/2025-12-16-LangChain-Deep-Agents-Skills
