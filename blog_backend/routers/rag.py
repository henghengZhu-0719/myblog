import os
import json
import logging
import asyncio
from typing import List, Optional

from fastapi import APIRouter, Form, UploadFile, File, Query
from fastapi.responses import JSONResponse, StreamingResponse

from pydantic import BaseModel

from agent.rag_service.ast_parser_service import MarkdownSectionParser

logger = logging.getLogger(__name__)

router = APIRouter()

_rag_graph = None


def get_rag_graph():
    global _rag_graph
    if _rag_graph is None:
        from agent.rag_service.rag_graph import RagGraph
        _rag_graph = RagGraph(top_k=10, use_reranker=True)
        logger.info("RagGraph 初始化成功")
    return _rag_graph


def init_rag_graph():
    """供 main.py startup 调用，提前初始化"""
    get_rag_graph()


class RagChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


@router.post("/rag/chat")
async def rag_chat(request: RagChatRequest):
    """基于知识库的 RAG 问答，SSE 流式返回"""

    async def generator():
        queue: asyncio.Queue = asyncio.Queue(maxsize=32)
        loop = asyncio.get_event_loop()

        def run_pipeline():
            try:
                rag = get_rag_graph()
                thread_id = request.user_id or "default"
                for event_type, data in rag.stream_answer(request.message, thread_id=thread_id):
                    loop.call_soon_threadsafe(queue.put_nowait, (event_type, data))
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, ("_error", str(e)))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("_done", None))

        task = loop.run_in_executor(None, run_pipeline)

        while True:
            event_type, data = await queue.get()
            if event_type == "_done":
                break
            if event_type == "_error":
                yield f"data: {json.dumps({'type': 'error', 'content': data})}\n\n"
                break

            if event_type == "rewrite":
                yield f"data: {json.dumps({'type': 'rewrite', 'dense_query': data['dense_query'], 'sparse_query': data['sparse_query']})}\n\n"
            elif event_type == "retrieve":
                chunks = data["chunks"]
                yield f"data: {json.dumps({'type': 'retrieve', 'total': len(chunks), 'chunks': chunks})}\n\n"
            elif event_type == "build_prompt":
                yield f"data: {json.dumps({'type': 'build_prompt', 'prompt_length': data['prompt_length']})}\n\n"
            elif event_type == "answer_token":
                yield f"data: {json.dumps({'type': 'text', 'content': data['token']})}\n\n"
            elif event_type == "answer_done":
                yield f"data: {json.dumps({'type': 'done', 'content': data['answer']})}\n\n"

        await task
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/rag/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    store_in_qdrant: bool = Form(False),
    chunk_size: int = Form(512),
    overlap: int = Form(50),
):
    """上传并解析 Markdown 文件，可选存入 Qdrant

    基于 AST 解析：
    - 精准识别标题层级、代码块、表格、图片、数学公式
    - 自动对图片生成语义描述、对代码块生成摘要（语义增强）
    - 保留标题路径用于结构化召回
    """
    results = []

    for file in files:
        raw = await file.read()
        filename = file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")

        if ext == ".md":
            parser = MarkdownSectionParser()
            chunks = await parser.parse_and_chunk(text, filename, chunk_size, overlap)
            dist = parser.statistics(chunks)
            chunk_infos = [
                {
                    "content": c.content,
                    "headings": c.headings,
                    "length": len(c.content),
                    "token_count": c.metadata.token_count if hasattr(c, 'metadata') else 0,
                    "line_start": c.metadata.line_start if hasattr(c, 'metadata') else 0,
                    "line_end": c.metadata.line_end if hasattr(c, 'metadata') else 0,
                }
                for c in chunks
            ]
        else:
            continue
        qdrant_stored = False
        qdrant_error: str | None = None

        if store_in_qdrant and chunks:
            try:
                from agent.rag_service.embedding_service import EmbeddingService
                from agent.rag_service.SparseEncoder_service import SparseEncoder
                from agent.rag_service.vector_store import VectorStore

                store_chunks = chunks
                embedder = EmbeddingService()
                sparse_encoder = SparseEncoder()
                vstore = VectorStore(embedder=embedder, sparse_encoder=sparse_encoder)
                vstore.store_chunks(store_chunks, source_file=filename)
                qdrant_stored = True
            except Exception as e:
                qdrant_error = str(e)
                logger.warning("Qdrant 存储失败: %s", e)

        results.append(
            {
                "filename": filename,
                "chunk_count": len(chunk_infos),
                "chunks": chunk_infos,
                "qdrant_stored": qdrant_stored,
                "qdrant_error": qdrant_error,
                "distribution": {
                    "total_chunks": dist.total_chunks,
                    "total_tokens": dist.total_tokens,
                    "total_chars": dist.total_chars,
                    "token_min": dist.token_min,
                    "token_max": dist.token_max,
                    "token_mean": round(dist.token_mean, 1),
                    "token_median": dist.token_median,
                    "token_p25": dist.token_p25,
                    "token_p75": dist.token_p75,
                    "token_p95": dist.token_p95,
                    "empty_chunks": len(dist.empty_chunks),
                    "too_small_chunks": len(dist.too_small_chunks),
                    "too_large_chunks": len(dist.too_large_chunks),
                    "orphan_chunks": len(dist.orphan_chunks),
                    "type_counts": dist.type_counts,
                },
            }
        )

    return JSONResponse({"results": results})


@router.get("/rag/search")
async def search_rag(
    query: str = Query(..., description="检索查询文本"),
    top_k: int = Query(5, ge=1, le=50, description="返回结果数"),
    use_reranker: bool = Query(False, description="是否使用重排序"),
):
    """从 Qdrant 向量库中检索与 query 最相关的文档片段"""
    try:
        from agent.rag_service.embedding_service import EmbeddingService
        from agent.rag_service.SparseEncoder_service import SparseEncoder
        from agent.rag_service.vector_store import VectorStore
        from agent.rag_service.reranker_service import RerankerService

        embedder = EmbeddingService()
        sparse_encoder = SparseEncoder()
        vstore = VectorStore(embedder=embedder, sparse_encoder=sparse_encoder)

        reranker = RerankerService() if use_reranker else None
        results = vstore.search(query, top_k=top_k, reranker=reranker)

        return JSONResponse({
            "query": query,
            "total": len(results),
            "use_reranker": use_reranker,
            "results": [r.to_dict() for r in results],
        })

    except Exception as e:
        logger.error("检索失败: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)
