from pprint import pprint
from services.chunk_service import ChunkService


def main():
    service = ChunkService(
        chunk_size=1024,
        chunk_overlap=10,
        min_chunk_size=50
    )

    text = """# 企业级升级路线图

> 基于当前技术栈（FastAPI + React + MySQL + LangChain + Anthropic SDK），向企业级 AI 平台演进的方向。

---

## 一、RAG 知识库系统

**目标**：让用户能对自己的博客、简历、职位数据进行自然语言问答。

### 核心方向
- **文档向量化**：博客文章 / 职位描述 → Embedding → 向量数据库（Chroma / Qdrant / Weaviate）
- **混合检索**：向量相似度 + BM25 关键词检索，提升召回率
- **多租户隔离**：每个用户的知识库独立命名空间
- **增量更新**：新增/修改文章时自动触发 re-embedding pipeline

### 技术选型
```
LangChain → 文档加载 / 分块 / 检索链
Qdrant    → 向量存储（支持 Docker 自托管）
BGE-M3    → 中文 Embedding 模型（本地 or API）
Reranker  → Cross-encoder 精排（提升准确率）
```

### 落地步骤
1. 博客文章 RAG 问答（最小 MVP）
2. 职位数据语义搜索（"找北京 3 年经验的 Python 岗"）
3. 简历与 JD 匹配度分析

---

## 二、智能体（Agent）系统

**目标**：从单次问答升级为能自主规划、调用工具、完成多步任务的 AI Agent。

### 核心方向

#### 2.1 求职 Agent
- 自动搜索职位 → 分析匹配度 → 生成定制化简历/Cover Letter → 追踪投递状态
- 工具：`search_jobs()` / `analyze_jd()` / `generate_resume()` / `send_application()`

#### 2.2 内容创作 Agent
- 给定主题 → 搜索资料 → 生成博客草稿 → 自动发布
- 工具：`web_search()` / `draft_post()` / `publish_post()`

#### 2.3 财务分析 Agent
- 定期汇总账单 → 生成消费报告 → 异常检测 → 主动提醒
- 工具：`query_expenses()` / `generate_report()` / `send_notification()`

### 技术选型
```
LangGraph          → Agent 状态机编排（支持循环、条件分支）
Anthropic SDK      → Claude 作为推理核心（已集成）
Tool Use / MCP     → 标准化工具调用协议
Redis              → Agent 会话状态持久化
Celery + Redis     → 异步长任务执行
```

### 架构模式
```
用户请求 → Planner Agent（任务分解）
              ↓
         Sub-Agents（并行执行子任务）
              ↓
         Critic Agent（结果校验）
              ↓
         用户反馈
```

---

## 三、数据管道 & 实时处理

**目标**：从定时爬取升级为事件驱动的实时数据流。

- **消息队列**：Kafka / RabbitMQ 解耦爬虫与处理逻辑
- **流式处理**：新职位发布 → 实时 Embedding → 推送匹配提醒
- **数据湖**：原始数据归档（MinIO / S3），支持历史回溯分析
- **ETL Pipeline**：Airflow 调度，替代现有 Playwright 定时任务

---

## 四、可观测性 & 评估体系

**目标**：AI 系统必须可测量、可调试、可改进。

### LLM 可观测性
- **LangSmith / Langfuse**：追踪每次 LLM 调用的 prompt、输出、延迟、费用
- **RAG 评估**：Context Precision / Recall / Answer Faithfulness（用 RAGAS 框架）
- **A/B 测试**：不同 prompt 策略的效果对比

### 系统监控
```
Prometheus + Grafana  → API 延迟、错误率、吞吐量
Sentry                → 异常追踪
结构化日志（JSON）     → ELK Stack 或 Loki
```

---

## 五、安全 & 多租户

**目标**：从个人项目升级为可服务多用户的平台。

- **认证升级**：JWT → OAuth2 + PKCE，支持第三方登录（GitHub / Google）
- **RBAC 权限**：角色（Admin / User / Guest）+ 资源级权限控制
- **API 限流**：Redis 令牌桶，防止滥用
- **数据隔离**：Row-level Security（PostgreSQL）或 tenant_id 分区
- **Prompt 注入防护**：输入过滤 + 输出校验

---

## 六、基础设施升级

**目标**：从 Docker Compose 单机部署升级为云原生架构。

```
当前：Docker Compose（单机）
  ↓
阶段一：Docker Compose + 外部托管数据库（RDS / PlanetScale）
  ↓
阶段二：Kubernetes（K3s 自托管 or 云托管）
  ↓
阶段三：Serverless 混合（无状态 API → Lambda/Cloud Run）
```

### 关键组件
- **CI/CD**：GitHub Actions → 自动测试 + 镜像构建 + 部署
- **配置管理**：Vault / AWS Secrets Manager 替代 .env 文件
- **CDN**：静态资源 + API 缓存（Cloudflare）

---

## 七、推荐优先级

| 优先级 | 方向 | 预估工作量 | 业务价值 |
|--------|------|-----------|---------|
| ⭐⭐⭐ | 博客 RAG 问答 | 1-2 周 | 高 |
| ⭐⭐⭐ | 求职 Agent MVP | 2-3 周 | 高 |
| ⭐⭐ | LLM 可观测性接入 | 3-5 天 | 中 |
| ⭐⭐ | 认证 & RBAC 升级 | 1-2 周 | 中 |
| ⭐ | Kafka 数据管道 | 3-4 周 | 中（规模化后） |
| ⭐ | K8s 迁移 | 4-6 周 | 低（当前阶段） |

---

## 八、最小可行路径（建议起点）

```
Week 1-2: 博客文章 RAG
  → 接入 Qdrant，实现文章向量化 + 问答接口

Week 3-4: 求职 Agent v1
  → LangGraph 实现 JD 分析 + 简历匹配 Agent

Week 5-6: 可观测性
  → Langfuse 接入，开始收集 LLM 调用数据

Week 7+: 根据数据反馈迭代
```

---

*生成时间：2026-04-20 | 基于当前 feat/rag 分支状态*

"""

    print("===== sections =====")
    sections = service._parse_sections(text)
    pprint(sections)

    print("\n===== chunks =====")
    chunks = service.split_text(text)
    for i, c in enumerate(chunks, 1):
        print(f"\n--- chunk {i} ---")
        pprint(c)


if __name__ == "__main__":
    main()