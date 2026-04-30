import os
import logging
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIMENSIONS = 1024

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "MyBlog")


class EmbeddingService:
    def __init__(
        self,
        qdrant_host: str = QDRANT_HOST,
        qdrant_port: int = QDRANT_PORT,
        collection: str = QDRANT_COLLECTION,
    ):
        self.collection = collection

        self.embed_client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )
        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)

    # ------------------------------------------------------------------
    #  Embedding
    # ------------------------------------------------------------------

    EMBED_BATCH_SIZE = 10

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_embeddings = []
        for start in range(0, len(texts), self.EMBED_BATCH_SIZE):
            batch = texts[start : start + self.EMBED_BATCH_SIZE]
            response = self.embed_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings

    # ------------------------------------------------------------------
    #  Collection 管理
    # ------------------------------------------------------------------

    VECTOR_NAME = "dense-vector"

    def ensure_collection(self):
        collections = self.qdrant.get_collections().collections
        if not any(c.name == self.collection for c in collections):
            self.qdrant.create_collection(
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
        self.qdrant.delete_collection(collection_name=self.collection)
        logger.info(f"Deleted collection '{self.collection}'")

    # ------------------------------------------------------------------
    #  写入
    # ------------------------------------------------------------------

    def store_chunks(
        self,
        chunks: list,
        source_file: str = "",
        batch_size: int = 20,
    ):
        self.ensure_collection()

        texts = [c.content for c in chunks]
        vectors = self.embed_texts(texts)

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            points.append(PointStruct(
                id=i,
                vector={self.VECTOR_NAME: vector},
                payload={
                    "content": chunk.content,
                    "headings": chunk.headings,
                    "chunk_index": i,
                    "source_file": source_file,
                },
            ))

        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            self.qdrant.upsert(
                collection_name=self.collection,
                points=batch,
            )

        logger.info(f"Stored {len(points)} chunks into '{self.collection}'")

    # ------------------------------------------------------------------
    #  检索
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> list[dict]:
        query_vector = self.embed_texts([query])[0]

        kwargs = dict(
            collection_name=self.collection,
            query=query_vector,
            using=self.VECTOR_NAME,
            limit=top_k,
            with_payload=True,
        )
        if score_threshold is not None:
            kwargs["score_threshold"] = score_threshold

        hits = self.qdrant.query_points(**kwargs).points

        return [
            {
                "content":     hit.payload.get("content", ""),
                "headings":    hit.payload.get("headings", []),
                "source_file": hit.payload.get("source_file", ""),
                "score":       hit.score,
            }
            for hit in hits
        ]
