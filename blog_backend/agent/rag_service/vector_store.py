import os
import logging
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from embedding_service import EmbeddingService, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "MyBlog")


@dataclass
class SearchResult:
    """检索结果的结构体"""
    content: str
    headings: list[str] = field(default_factory=list)
    source_file: str = ""
    score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "headings": self.headings,
            "source_file": self.source_file,
            "score": self.score,
        }


class VectorStore:
    def __init__(
        self,
        embedder: EmbeddingService,
        collection: str = QDRANT_COLLECTION,
        host: str = QDRANT_HOST,
        port: int = QDRANT_PORT,
        vector_name: str = "dense-vector",
        upsert_batch_size: int = 20,
    ):
        self.embedder = embedder
        self.collection = collection
        self.VECTOR_NAME = vector_name
        self.UPSERT_BATCH_SIZE = upsert_batch_size
        self.client = QdrantClient(host=host, port=port)

    # ---------- Collection 管理 ----------

    def ensure_collection(self):
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection for c in collections):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    self.VECTOR_NAME: VectorParams(
                        size=EMBEDDING_DIMENSIONS,
                        distance=Distance.COSINE,
                    ),
                },
            )
            logger.info(f"Created collection '{self.collection}'")

    def delete_collection(self):
        self.client.delete_collection(collection_name=self.collection)
        logger.info(f"Deleted collection '{self.collection}'")

    # ---------- 写入 ----------

    def store_chunks(self, chunks: list, source_file: str = ""):
        self.ensure_collection()

        texts = [c.content for c in chunks]
        vectors = self.embedder.embed_documents(texts)

        points = [
            PointStruct(
                id=i,
                vector={self.VECTOR_NAME: vector},
                payload={
                    "content":     chunk.content,
                    "headings":    chunk.headings,
                    "chunk_index": i,
                    "source_file": source_file,
                },
            )
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]

        for start in range(0, len(points), self.UPSERT_BATCH_SIZE):
            self.client.upsert(
                collection_name=self.collection,
                points=points[start : start + self.UPSERT_BATCH_SIZE],
            )

        logger.info(f"Stored {len(points)} chunks into '{self.collection}'")

    # ---------- 检索 ----------

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> list[SearchResult]:
        query_vector = self.embedder.embed_query(query)

        kwargs = dict(
            collection_name=self.collection,
            query=query_vector,
            using=self.VECTOR_NAME,
            limit=top_k,
            with_payload=True,
        )
        if score_threshold is not None:
            kwargs["score_threshold"] = score_threshold

        hits = self.client.query_points(**kwargs).points

        return [
            SearchResult(
                content=hit.payload.get("content", ""),
                headings=hit.payload.get("headings", []),
                source_file=hit.payload.get("source_file", ""),
                score=hit.score,
            )
            for hit in hits
        ]
