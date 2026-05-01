import os
import logging
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Fusion,
    FusionQuery,
    PointStruct,
    Prefetch,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

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
        sparse_encoder,
        collection: str = QDRANT_COLLECTION,
        host: str = QDRANT_HOST,
        port: int = QDRANT_PORT,
        vector_name: str = "dense-vector",
        sparse_vector_name: str = "sparse-vector",
        upsert_batch_size: int = 20,
    ):
        self.embedder = embedder
        self.sparse_encoder = sparse_encoder
        self.collection = collection
        self.VECTOR_NAME = vector_name
        self.SPARSE_VECTOR_NAME = sparse_vector_name
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
                sparse_vectors_config={
                    self.SPARSE_VECTOR_NAME: SparseVectorParams(
                        index=SparseIndexParams(on_disk=True)
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
        dense_vectors = self.embedder.embed_documents(texts)
        sparse_vectors = self.sparse_encoder.encode_documents(texts)

        points = [
            PointStruct(
                id=i,
                vector={
                    self.VECTOR_NAME: dense_vector,
                    self.SPARSE_VECTOR_NAME: sparse_vector,
                },
                payload={
                    "content":     chunk.content,
                    "headings":    chunk.headings,
                    "chunk_index": i,
                    "source_file": source_file,
                },
            )
            for i, (chunk, dense_vector, sparse_vector) in enumerate(
                zip(chunks, dense_vectors, sparse_vectors)
            )
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
        dense_vector = self.embedder.embed_query(query)
        sparse_vector = self.sparse_encoder.encode_query(query)

        kwargs = dict(
            collection_name=self.collection,
            prefetch=[
                Prefetch(
                    query=dense_vector,
                    using=self.VECTOR_NAME,
                    limit=top_k * 2,
                ),
                Prefetch(
                    query=sparse_vector,
                    using=self.SPARSE_VECTOR_NAME,
                    limit=top_k * 2,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
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
