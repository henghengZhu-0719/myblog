import os
import logging

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIMENSIONS = 1024


class EmbeddingService:
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self._client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转为向量列表，自动分批处理。"""
        all_embeddings = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = self._client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in sorted_data])
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """单条文本转向量的便捷方法。"""
        return self.embed_documents([text])[0]
