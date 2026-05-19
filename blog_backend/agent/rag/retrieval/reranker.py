import logging
from typing import Optional

import httpx

from agent.rag.config import DASHSCOPE_API_KEY, RERANK_MODEL, RERANK_MAX_DOCS
from agent.rag.models.search import SearchResult

logger = logging.getLogger(__name__)


class RerankerService:
    """基于 DashScope qwen3-rerank 模型的重排序服务"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = RERANK_MODEL,
    ):
        self._api_key = api_key or DASHSCOPE_API_KEY
        self._model = model

    def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_k: int = 5,
    ) -> list[SearchResult]:
        if not candidates:
            return []
        if len(candidates) <= 1:
            return candidates

        pairs = [(c.content[:2000], c) for c in candidates]
        pairs = [(t, c) for t, c in pairs if t.strip()]
        if not pairs:
            logger.warning("Rerank: 所有候选文档均为空，跳过重排序")
            return candidates[:top_k]
        if len(pairs) < len(candidates):
            logger.info("Rerank: %d 个文档因内容为空被过滤", len(candidates) - len(pairs))
        if len(pairs) > RERANK_MAX_DOCS:
            logger.info("Rerank: 文档数 %d 超过限制 %d，截断", len(pairs), RERANK_MAX_DOCS)
            pairs = pairs[:RERANK_MAX_DOCS]

        texts, valid_candidates = zip(*pairs)
        try:
            scores = self._call_rerank_api(query, list(texts))
        except Exception:
            logger.warning("Rerank 降级：保留原始候选顺序，返回前 %d 条", top_k)
            return candidates[:top_k]

        scored = list(zip(scores, valid_candidates))
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            SearchResult(
                content=r.content,
                headings=r.headings,
                source_file=r.source_file,
                score=score,
                content_types=r.content_types,
                token_count=r.token_count,
                char_count=r.char_count,
                raw_code=r.raw_code,
                section_level=r.section_level,
                prev_chunk_index=r.prev_chunk_index,
                next_chunk_index=r.next_chunk_index,
            )
            for score, r in scored[:top_k]
        ]

    def _call_rerank_api(
        self,
        query: str,
        documents: list[str],
    ) -> list[float]:
        url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": {
                "top_n": len(documents),
            },
        }

        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.warning(
                        "Rerank API 返回 %s: body=%s",
                        resp.status_code, resp.text[:1000],
                    )
                resp.raise_for_status()
                data = resp.json()
            results = data["output"]["results"]
            sorted_results = sorted(results, key=lambda x: x["index"])
            return [item["relevance_score"] for item in sorted_results]
        except Exception as e:
            logger.warning("Rerank API 调用失败: %s", e)
            raise
