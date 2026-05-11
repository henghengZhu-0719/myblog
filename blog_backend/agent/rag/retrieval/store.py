import logging
from typing import Optional

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

from agent.rag.config import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    EMBEDDING_DIMENSIONS,
)
from agent.rag.models.search import SearchResult
from agent.rag.retrieval.dense import EmbeddingService
from agent.rag.retrieval.reranker import RerankerService

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        embedder: EmbeddingService,
        sparse_encoder,
        collection:         str = QDRANT_COLLECTION,
        host:               str = QDRANT_HOST,
        port:               int = QDRANT_PORT,
        vector_name:        str = "dense-vector",
        sparse_vector_name: str = "sparse-vector",
        upsert_batch_size:  int = 20,
    ):
        self.embedder            = embedder
        self.sparse_encoder      = sparse_encoder
        self.collection          = collection
        self.VECTOR_NAME         = vector_name
        self.SPARSE_VECTOR_NAME  = sparse_vector_name
        self.UPSERT_BATCH_SIZE   = upsert_batch_size
        self.client              = QdrantClient(host=host, port=port)

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
            logger.info("Created collection '%s'", self.collection)

    def delete_collection(self):
        self.client.delete_collection(collection_name=self.collection)
        logger.info("Deleted collection '%s'", self.collection)

    def _next_id(self) -> int:
        return self.client.count(collection_name=self.collection).count

    def store_chunks(self, chunks: list, source_file: str = ""):
        self.ensure_collection()
        offset         = self._next_id()
        texts          = [c.content for c in chunks]
        dense_vectors  = self.embedder.embed_documents(texts)
        sparse_vectors = self.sparse_encoder.encode_documents(texts)

        def _meta(chunk, attr, default):
            if hasattr(chunk, "metadata") and chunk.metadata is not None:
                return getattr(chunk.metadata, attr, default)
            return default

        points = []
        for i, (chunk, dense_vector, sparse_vector) in enumerate(
            zip(chunks, dense_vectors, sparse_vectors)
        ):
            token_count   = _meta(chunk, "token_count",    0)
            char_count    = _meta(chunk, "char_count",      0)
            content_types = int(_meta(chunk, "content_types", 0))
            section_level = _meta(chunk, "section_level",   0)
            raw_code      = _meta(chunk, "raw_code",        "")

            if token_count == 0 and len(chunk.content) > 0:
                logger.warning(
                    "Chunk #%d token_count=0 but content is %d chars. "
                    "Metadata may be missing — was this chunk created by AST parser?",
                    offset + i, len(chunk.content),
                )

            points.append(PointStruct(
                id=offset + i,
                vector={
                    self.VECTOR_NAME:        dense_vector,
                    self.SPARSE_VECTOR_NAME: sparse_vector,
                },
                payload={
                    "content":          chunk.content,
                    "headings":         chunk.headings,
                    "chunk_index":      offset + i,
                    "source_file":      source_file,
                    "content_types":    content_types,
                    "token_count":      token_count,
                    "char_count":       char_count,
                    "raw_code":         raw_code,
                    "section_level":    section_level,
                    "prev_chunk_index": _meta(chunk, "prev_chunk_index", None),
                    "next_chunk_index": _meta(chunk, "next_chunk_index", None),
                },
            ))

        for start in range(0, len(points), self.UPSERT_BATCH_SIZE):
            self.client.upsert(
                collection_name=self.collection,
                points=points[start : start + self.UPSERT_BATCH_SIZE],
            )
        logger.info("Stored %d chunks into '%s'", len(points), self.collection)

    def search(
        self,
        dense_query:            str,
        sparse_query:           str,
        top_k:                  int            = 10,
        score_threshold:        Optional[float] = None,
        reranker:               Optional[RerankerService] = None,
        rerank_multiplier:      int            = 3,
        rerank_score_threshold: Optional[float] = None,
    ) -> list[SearchResult]:
        dense_vector  = self.embedder.embed_query(dense_query)
        sparse_vector = self.sparse_encoder.encode_query(sparse_query)

        prefetch_limit = top_k * (rerank_multiplier if reranker else 2)

        kwargs = dict(
            collection_name=self.collection,
            prefetch=[
                Prefetch(query=dense_vector,  using=self.VECTOR_NAME,       limit=prefetch_limit),
                Prefetch(query=sparse_vector, using=self.SPARSE_VECTOR_NAME, limit=prefetch_limit),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=prefetch_limit if reranker else top_k,
            with_payload=True,
        )

        if score_threshold is not None:
            kwargs["score_threshold"] = score_threshold

        hits = self.client.query_points(**kwargs).points
        logger.info("RRF 召回 %d 条候选 (prefetch_limit=%d)", len(hits), prefetch_limit)

        results = [
            SearchResult(
                content=hit.payload.get("content", ""),
                headings=hit.payload.get("headings", []),
                source_file=hit.payload.get("source_file", ""),
                score=hit.score,
                content_types=hit.payload.get("content_types", 0),
                token_count=hit.payload.get("token_count", 0),
                char_count=hit.payload.get("char_count", 0),
                raw_code=hit.payload.get("raw_code", ""),
                section_level=hit.payload.get("section_level", 0),
                prev_chunk_index=hit.payload.get("prev_chunk_index"),
                next_chunk_index=hit.payload.get("next_chunk_index"),
            )
            for hit in hits
        ]

        if reranker:
            results = reranker.rerank(dense_query, results, top_k=top_k)
            logger.info(
                "Reranker 精排后 %d 条，分数范围 [%.4f, %.4f]",
                len(results),
                results[-1].score if results else 0.0,
                results[0].score  if results else 0.0,
            )
            if rerank_score_threshold is not None:
                before  = len(results)
                results = [r for r in results if r.score >= rerank_score_threshold]
                logger.info(
                    "Reranker 后过滤: %d → %d 条 (threshold=%.3f)",
                    before, len(results), rerank_score_threshold,
                )

        return results
