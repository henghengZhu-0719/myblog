import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── LLM（DeepSeek） ─────────────────────────────────
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
DEEPSEEK_MODEL    = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

# ── DashScope（阿里云：Embedding + Reranker + Vision） ──
DASHSCOPE_API_KEY  = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# Embedding
EMBEDDING_MODEL      = "text-embedding-v3"
EMBEDDING_DIMENSIONS = 1024

# Reranker
RERANK_MODEL               = "qwen3-rerank"
RERANK_MAX_SEGMENTS_PER_DOC = 10
RERANK_MAX_DOCS             = 20

# Vision
VISION_MODEL = "qwen-vl-max"

# ── Qdrant ──────────────────────────────────────────────
QDRANT_URL        = os.getenv("QDRANT_URL", "http://192.168.1.8:6333")
QDRANT_HOST       = os.getenv("QDRANT_HOST", "192.168.1.8")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "MyBlog")
