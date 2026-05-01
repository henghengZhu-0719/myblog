"""端到端测试：Markdown 解析 → 向量化 → 存入 Qdrant → 检索"""

from md_parser_service import MarkdownParserService
from embedding_service import EmbeddingService
from vector_store import VectorStore

CHUNK_SIZE = 500
OVERLAP = 100

SOURCE_FILE = "/Users/zhuyq/Desktop/DeepAgents.md"

# ========== 1. 解析 Markdown ==========
print("=" * 60)
print("1. 解析 Markdown")
print("=" * 60)

parser = MarkdownParserService(chunk_size=CHUNK_SIZE, overlap=OVERLAP)

with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    text = f.read()

chunks = parser.split_markdown_into_chunks(text, CHUNK_SIZE, OVERLAP)
print(f"共切分为 {len(chunks)} 个 chunk\n")
for i, chunk in enumerate(chunks):
    print(f"【Chunk {i+1}】长度={len(chunk.content):>5}  headings={chunk.headings}")

# ========== 2. 向量化 & 存入 Qdrant ==========
print("\n" + "=" * 60)
print("2. 向量化 & 存入 Qdrant")
print("=" * 60)

embedder = EmbeddingService()
store = VectorStore(embedder=embedder)

store.store_chunks(chunks, source_file=SOURCE_FILE)
print("写入完成！")

# ========== 3. 检索测试 ==========
print("\n" + "=" * 60)
print("3. 检索测试")
print("=" * 60)

test_queries = [
    "XGBoost是什么？",
    "堆叠回归模型能干什么在房地产领域？",
]

for query in test_queries:
    print(f"\n查询：{query}")
    print("-" * 40)
    results = store.search(query, top_k=2)
    for r in results:
        print(f"  相关度: {r.score:.4f}")
        print(f"  标题路径: {' > '.join(r.headings)}")
        print(f"  内容预览: {r.content[:120]}...")
        print()
