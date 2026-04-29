# DeepAgents 记忆系统

## 概述

DeepAgents 的记忆系统是一种基于 **AGENTS.md 规范** 的持久化上下文注入机制。与常规的会话记忆不同，DeepAgents 的记忆不是从历史对话中自动提取的，而是由开发者预先编写的、以 Markdown 文件形式存在的**静态上下文**。这些文件在每次 Agent 启动时被加载并注入到系统提示词中，为 Agent 提供项目级别的长期记忆和运行指导。

该系统的核心思想是：**Agent 是无状态的**。每次新的会话，Agent 都会回到其通用训练权重。记忆系统通过提供稳定、不易变化的项目上下文，帮助 Agent 保持对项目的"制度性判断"——如何解决歧义、何时需要询问、哪些架构价值观需要坚持。

***

## 核心架构

记忆系统由三个关键层级构成：

### 1. MemoryMiddleware（记忆中间件）

`MemoryMiddleware` 是记忆系统的核心。它作为一个中间件挂载在 Agent 的执行管道中，负责从配置的数据源加载 `AGENTS.md` 文件，并将其内容注入到系统提示词中。

```
from deepagents import MemoryMiddleware
from deepagents.backends.filesystem import FilesystemBackend

backend = FilesystemBackend(root_dir="/")
middleware = MemoryMiddleware(
    backend=backend,
    sources=[
        "~/.deepagents/AGENTS.md",
        "./.deepagents/AGENTS.md",
    ],
)
```

**主要方法和生命周期**：

- **`before_agent()`**：在 Agent 执行之前加载记忆内容。从所有配置的源读取文件，并存储到中间件状态中。仅在状态中尚未存在记忆内容时执行加载（避免重复加载）。
- **`modify_request()`**：将加载的记忆内容注入到系统消息中，使记忆成为 Agent 初始上下文的一部分。
- \*\*`wrap_model_cal()`：在模型调用时包装系统提示词，确保记忆内容始终存在于上下文中。

### 2. 后端系统（Backend）

记忆系统采用**可插拔后端**架构，通过统一的 `BackendProtocol` 接口支持多种存储方式：

| 后端类型                | 说明                      | 适用场景              |
| ------------------- | ----------------------- | ----------------- |
| `FilesystemBackend` | 直接读写文件系统                | 本地开发 CLI、CI/CD 管道 |
| `StateBackend`      | 存储于内存状态                 | Web 服务、生产环境       |
| `StoreBackend`      | 基于 LangGraph Store 的持久化 | 需要长期持久化的场景        |
| `SandboxBackend`    | 沙盒隔离环境                  | 运行不可信工作负载         |
| `CompositeBackend`  | 组合多个后端                  | 复杂的混合部署场景         |

其中 `FilesystemBackend` 是最常用的后端，它通过 `root_dir` 参数控制访问范围，支持 `virtual_mode` 提供虚路径安全防护。

### 3. 记忆源（Memory Sources）

记忆源是指向 `AGENTS.md` 文件的路径列表。多个源按顺序加载、串联合并，后加载的内容出现在提示词的后面。典型配置包含两个层级：

```
sources = [
    "~/.deepagents/AGENTS.md",   # 用户级别的全局记忆
    "./.deepagents/AGENTS.md",   # 项目级别的记忆
]
```

***

## 记忆的加载与注入流程

记忆系统的完整工作流程如下：

1. **Agent 启动**：调用 `create_deep_agent(memory=[...])` 或手动创建 `MemoryMiddleware`
2. **初始化**：中间件将 `memory` 参数中的路径解析为 `MemorySource` 列表
3. **`before_agent`** **阶段**：逐一遍历所有源路径，通过后端读取文件内容。如果一次会话中有多个调用，中间件会检查状态缓存，避免重复加载
4. **`modify_request`** **阶段**：将读取到的文件内容格式化为系统消息文本，追加到已有的系统提示词之后
5. **模型调用**：Agent 在增强后的系统提示词指导下运行

```Python
create_deep_agent(
    model="claude-sonnet-4-6",
    memory=["/memory/AGENTS.md"],
    ...
)
```

在 `create_deep_agent` 的中间件执行顺序中，`MemoryMiddleware` 位于尾堆栈（tail stack），在大多数用户中间件之后执行，确保记忆内容是最晚添加的上下文之一。

***

## AGENTS.md 文件规范

`AGENTS.md` 是记忆系统的载体文件，遵循以下设计哲学：

### 核心原则

1. **最小化设计**：研究（Gloaguen 等, 2026）表明，LLM 生成的上下文文件会降低 Agent 任务成功率并增加推理成本。开发者编写的上下文文件仅在保持最小化和精确时才提供正面效果。
2. **工具链优先**：如果约束条件可以被 linter、格式化工具、类型检查器等工具强制执行，则不应写入 `AGENTS.md`。该文件只承载工具无法表达的内容。
3. **负面约束不写入**：告诉 Agent "不要做什么" 反而会让这个概念在注意力机制中更突出（"粉红大象问题"）。

### 推荐的章节结构

| 章节                      | 内容              | 示例                               |
| ----------------------- | --------------- | -------------------------------- |
| **Mission**             | 项目目的和核心约束       | "Local-first 数据架构，离线支持不可妥协"      |
| **Toolchain**           | 构建、测试、lint 等命令  | `pnpm build` `pnpm test:unit`    |
| **Judgment Boundaries** | 无法用工具表达的行为规则    | NEVER 提交密钥，ASK 前添加依赖，ALWAYS 解释计划 |
| **Personas**            | 可用的 Agent 角色注册表 | 仅注册名称和调用方式，定义写在 skill 文件中        |
| **Context Map**         | 代码库结构索引         | 高层次的架构指引                         |

***

## 记忆 vs. 技能的区分

记忆系统与技能系统（Skills）有明确的职责划分：

| 维度       | 记忆 (Memory)    | 技能 (Skills)    |
| -------- | -------------- | -------------- |
| **加载方式** | 始终加载，每次启动自动注入  | 按需调用，通过名称显式触发  |
| **内容特征** | 稳定、不易变化的上下文    | 可执行的工作流程       |
| **文件位置** | `AGENTS.md`    | 技能目录下的文件       |
| **更新频率** | 低频更改           | 可频繁更新          |
| **典型用途** | 项目概述、架构原则、边界规则 | 代码审查、部署流程、测试模式 |

***

## 状态管理

`MemoryMiddleware` 定义了两个状态类进行状态管理：

- **`MemoryState`**：存储已加载的记忆内容。包含来源路径和对应的文件内容字典。
- **`MemoryStateUpdate`**：定义状态更新的结构。用于在中间件链中传递新的记忆内容。

这种设计确保了：

- 同一会话中不会重复加载记忆文件
- 中间件链中的其他组件可以读取已加载的记忆内容
- 状态可以在 Agent 运行过程中被更新

***

## 安全考虑

使用 `FilesystemBackend` 时存在以下安全风险：

- Agent 可以读取任何可访问的文件，包括密钥和 `.env` 文件
- 结合网络工具，密钥可能通过 SSRF 攻击被外泄
- 文件修改是持久且不可逆的

**推荐的防护措施**：

1. 启用人工审批（HITL）中间件审查敏感操作
2. 将密钥排除在可访问的文件系统路径之外
3. 在生产环境中优先使用 `StateBackend` 或 `SandboxBackend`

***

## 配置示例

以下是一个完整的记忆系统配置示例：

```python
from deepagents import MemoryMiddleware, create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

# 配置记忆中间件
memory_middleware = MemoryMiddleware(
    backend=FilesystemBackend(root_dir="/"),
    sources=[
        "~/.deepagents/AGENTS.md",      # 全局配置
        "./.deepagents/AGENTS.md",      # 项目配置
        "./AGENTS.md",                  # 根目录配置
    ],
    add_cache_control=True,             # 启用提示缓存
)

# 创建带记忆功能的 Agent
agent = create_deep_agent(
    model="claude-sonnet-4-6",
    middleware=[memory_middleware],
    # 或通过 memory 参数快捷指定
    # memory=["/AGENTS.md"],
)
```

***

## 总结

DeepAgents 的记忆系统是一个基于文件的长期上下文注入机制。它通过 `MemoryMiddleware` 在 Agent 启动时加载 `AGENTS.md` 文件并注入系统提示词，为无状态的 Agent 提供项目级别的制度性记忆。该系统采用可插拔后端架构支持不同的存储场景，并通过清晰的最小化设计原则确保记忆内容的高信噪比。

### Sources

\[1] DeepAgents Memory Middleware Reference: <https://reference.langchain.com/python/deepagents/middleware/memory/MemoryMiddleware>
\[2] DeepAgents memory module overview: <https://reference.langchain.com/python/deepagents/middleware/memory>
\[3] AGENTS.md Specification Guide: <https://asdlc.io/practices/agents-md-spec/>
\[4] FilesystemBackend Reference: <https://reference.langchain.com/python/deepagents/backends/filesystem/FilesystemBackend>
\[5] create\_deep\_agent Reference: <https://reference.langchain.com/python/deepagents/graph/create_deep_agent>
\[6] DeepAgents Backends Overview: <https://docs.langchain.com/oss/python/deepagents/backends>
