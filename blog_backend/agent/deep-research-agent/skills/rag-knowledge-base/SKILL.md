---
name: rag-knowledge-base
description: 当用户提出任何可能由知识库回答的问题时使用此技能，包括领域专项查询、文档查找、
  技术问题，或任何"搜索"、"查找"、"检索"已存储文档信息的请求。
---

# rag-knowledge-base

## 概述

本技能通过调用本地 RAG（检索增强生成）API，从知识库中检索相关文档片段并生成有据可查的回答。

## 可用接口

### 1. 完整 RAG 问答（流式）
- **URL**: `http://localhost:8000/rag/chat`
- **方法**: POST
- **Content-Type**: application/json
- **请求体**:
  ```json
  {
    "message": "<用户问题>",
    "user_id": "agent-session"
  }
  ```
- **响应**: SSE 流，包含以下事件类型：
  - `intent` — 识别到的查询意图
  - `rewrite` — 改写后的稠密/稀疏查询
  - `retrieve` — 检索到的文档片段及相关性分数
  - `build_prompt` — 提示词构建信息
  - `text` — 流式返回的回答 token
  - `done` — 最终完整回答

### 2. 仅检索（不生成回答）
- **URL**: `http://localhost:8000/rag/search`
- **方法**: GET
- **参数**:
  - `query`（必填）：检索文本
  - `top_k`（默认 5，最大 50）：返回结果数
  - `use_reranker`（默认 false）：是否启用重排序
- **响应**:
  ```json
  {
    "query": "...",
    "total": 5,
    "results": [
      { "content": "...", "score": 0.92, "source": "..." }
    ]
  }
  ```

### 3. 上传文档
- **URL**: `http://localhost:8000/rag/upload`
- **方法**: POST
- **Content-Type**: multipart/form-data
- **字段**:
  - `files`：一个或多个 `.md` 文件
  - `store_in_qdrant`（bool，默认 false）：是否持久化到向量库
  - `chunk_size`（int，默认 512）
  - `overlap`（int，默认 50）

## 使用指令

### 当用户就知识库内容提问时：
1. 携带用户消息调用 `POST /rag/chat`。
2. 持续读取 SSE 流，直到收到 `done` 事件。
3. 将 `done` 事件中的 `content` 字段作为最终回答。
4. 若 `retrieve` 事件显示 chunks 数量为 0，告知用户未找到相关文档。

### 当用户只需检索、不需要生成回答时：
1. 调用 `GET /rag/search?query=<问题>&top_k=5&use_reranker=true`。
2. 将返回的文档片段连同来源和分数一并呈现给用户。
3. 分数低于 0.5 的片段应视为低置信度结果。

### 当用户需要上传文档时：
1. 携带文件及 `store_in_qdrant=true` 调用 `POST /rag/upload`。
2. 向用户汇报 `chunk_count` 和 `distribution` 统计摘要。
3. 若 `qdrant_error` 不为空，清晰地向用户报告错误信息。
```