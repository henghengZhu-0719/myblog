---
name: "rag-retrieval"
description: "Hybrid search (dense + sparse) + reranking via Qdrant vector store. Invoke when user asks to search/query knowledge base, retrieve relevant docs, or perform semantic search."
---

# RAG Retrieval

Hybrid retrieval system combining dense semantic vectors (DashScope text-embedding-v3) and sparse keyword vectors (BM25) with RRF fusion, plus optional reranking via DashScope qwen3-rerank.

## Architecture

```
User Query
    │
    ▼
EmbeddingService (dense)    SparseEncoder (BM25)
    │                            │
    ▼                            ▼
dense_vector              sparse_vector
    │                            │
    └──────────┬─────────────────┘
               ▼
      VectorStore.search()
         RRF Fusion
               │
               ▼
         Candidates
               │
               ▼
    ┌─ reranker=Y ──► RerankerService ──► ranked results
    └─ reranker=N ──► direct results
```

## Components

### EmbeddingService
Dense embedding via DashScope `text-embedding-v3` (1024 dimensions).
- [dense.py](file:///Users/zhuyq/blog/blog_backend/agent/rag/retrieval/dense.py)
- Config: [config.py](file:///Users/zhuyq/blog/blog_backend/agent/rag/config.py)

### SparseEncoder
BM25 sparse embedding via `fastembed` (local, no API needed).
- [sparse.py](file:///Users/zhuyq/blog/blog_backend/agent/rag/retrieval/sparse.py)

### VectorStore
Qdrant-based hybrid search with RRF (Reciprocal Rank Fusion).
- [store.py](file:///Users/zhuyq/blog/blog_backend/agent/rag/retrieval/store.py)

### RerankerService
Cross-encoder reranking via DashScope `qwen3-rerank`.
- [reranker.py](file:///Users/zhuyq/blog/blog_backend/agent/rag/retrieval/reranker.py)

### Data Models
- [search.py](file:///Users/zhuyq/blog/blog_backend/agent/rag/models/search.py) — `SearchResult` dataclass with `to_dict()`

## Usage

### Basic Search (no reranker)

```python
from agent.rag.retrieval.dense import EmbeddingService
from agent.rag.retrieval.sparse import SparseEncoder
from agent.rag.retrieval.store import VectorStore

embedder = EmbeddingService()
sparse_encoder = SparseEncoder()
vstore = VectorStore(embedder=embedder, sparse_encoder=sparse_encoder)

results = vstore.search(
    dense_query="your semantic query",
    sparse_query="bm25 keyword query",
    top_k=10,
)
```

### Search with Reranker

```python
from agent.rag.retrieval.reranker import RerankerService

reranker = RerankerService()
results = vstore.search(
    dense_query="your semantic query",
    sparse_query="bm25 keyword query",
    top_k=5,
    reranker=reranker,
    rerank_multiplier=3,  # fetch 3x candidates before reranking
    rerank_score_threshold=0.3,  # filter low-scoring results
)
```

### SearchResult Fields

| Field | Type | Description |
|-------|------|-------------|
| `content` | str | The chunk text |
| `headings` | list[str] | Heading hierarchy path |
| `source_file` | str | Origin filename |
| `score` | float | Relevance score (RRF or reranker) |
| `content_types` | int | Bitmask of ContentType flags |
| `token_count` | int | Estimated token count |
| `char_count` | int | Character count |
| `raw_code` | str | Raw code if chunk contains code block |
| `section_level` | int | Heading depth (0 = no heading) |
| `prev_chunk_index` | int | Previous chunk ID (for context assembly) |
| `next_chunk_index` | int | Next chunk ID (for context assembly) |

### Via REST API

```python
import httpx

# Pure search
resp = httpx.get("http://localhost:8000/rag/search", params={
    "query": "your question",
    "top_k": 5,
    "use_reranker": True,
})
data = resp.json()
for r in data["results"]:
    print(f"[{r['score']:.3f}] {r['content'][:100]}")
```

## Configuration

Key environment variables in [agent/rag/config.py](file:///Users/zhuyq/blog/blog_backend/agent/rag/config.py):

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHSCOPE_API_KEY` | — | Aliyun API key (embedding + reranker) |
| `EMBEDDING_MODEL` | `text-embedding-v3` | Dense embedding model |
| `EMBEDDING_DIMENSIONS` | `1024` | Dense vector dimensions |
| `RERANK_MODEL` | `qwen3-rerank` | Reranker model |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `QDRANT_COLLECTION` | `MyBlog` | Qdrant collection name |

## Best Practices

1. **Query rewriting**: For better results, use an LLM to rewrite questions into separate dense/sparse queries (see [graph.py](file:///Users/zhuyq/blog/blog_backend/agent/rag/pipeline/graph.py) `_rewrite_question`)
2. **Reranker tuning**: Start with `rerank_multiplier=3` and adjust based on latency vs quality tradeoff
3. **Score threshold**: Use `rerank_score_threshold` (e.g., 0.3) to filter irrelevant results
4. **Context assembly**: Use `prev_chunk_index`/`next_chunk_index` to retrieve surrounding context for better answer quality
5. **Collection isolation**: Use different collection names for different knowledge domains
