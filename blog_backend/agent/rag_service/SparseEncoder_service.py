from fastembed import SparseTextEmbedding
from qdrant_client.models import SparseVector  


class SparseEncoder:
    """BM25 稀疏向量编码器，本地运行，无需 API"""

    def __init__(self):
        self._model = SparseTextEmbedding(model_name="Qdrant/bm25")

    def encode_documents(self, texts: list[str]) -> list[SparseVector]:
        """写入时使用，直接返回 qdrant 的 SparseVector 对象"""
        embeddings = list(self._model.embed(texts))
        return [
            SparseVector(
                indices=e.indices.tolist(),
                values=e.values.tolist(),
            )
            for e in embeddings
        ]

    def encode_query(self, text: str) -> SparseVector:
        """查询时使用"""
        return self.encode_documents([text])[0]
