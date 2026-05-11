import json
import logging
import os
import sys
import re

from openai import OpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.rag.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from agent.rag.pipeline.state import RagState
from agent.rag.retrieval.dense import EmbeddingService
from agent.rag.retrieval.sparse import SparseEncoder
from agent.rag.retrieval.reranker import RerankerService
from agent.rag.retrieval.store import VectorStore

logger = logging.getLogger(__name__)

REWRITE_SYSTEM_PROMPT = """你是一名专业的搜索查询优化专家。你的任务是对用户的原始问题生成**两个不同侧重点**的搜索查询。

请严格按照以下 JSON 格式输出，不要任何额外内容：

```json
{
  "dense_query": "用于语义向量检索的查询，保留完整语义、自然句式，适合 embedding 匹配",
  "sparse_query": "用于 BM25 关键词检索的查询，精简关键词、去除停用词，适合词频精确匹配"
}
```

重写原则：
1. 去除冗余的问候语、语气词和无关表述
2. 保持原问题的核心意图不变
3. 如果存在对话历史，将历史语境融入新查询，使查询具有独立检索能力（不依赖历史也能检索到相关信息）
4. dense_query：语义丰富、完整句式，便于 embedding 理解
5. sparse_query：提取核心关键词，以空格分隔，便于 BM25 命中"""

REWRITE_USER_PROMPT = """{history_section}当前问题：{query}"""

INTENT_CLASSIFY_PROMPT = """你是一个智能路由判断专家。判断用户的问题是否需要检索本地知识库来回答。

分类规则：
- "rag"：用户询问知识性内容，涉及技术概念、原理、对比、应用等，需要从知识库中检索相关文档
- "chat"：闲聊、问候、情感交流、无关话题，不需要检索知识库，直接回复即可

请只返回一个词："rag" 或 "chat"，不要任何额外内容。

当前问题：{query}"""

CHAT_SYSTEM_PROMPT = """你是一个友好的博客助手，可以与用户进行自由对话。回答要简洁、自然、友好。

如果用户问的问题涉及技术概念，你可以根据自己的知识回答，但告知用户如果需要更详细的资料可以为你检索知识库。"""

RAG_SYSTEM_PROMPT = """你是一个专业的博客知识助手，基于提供的参考上下文回答用户问题。

回答要求：
1. 只基于参考上下文内容回答，不得编造任何信息
2. 如果上下文不足以回答，诚实地说"参考文档中未找到相关信息"
3. 回答中使用【文档N】标注每条事实的来源，N 为上下文中文档编号
4. 多文档回答时，确保不同来源的信息引用正确、不混淆
5. 回答要简洁、准确、有条理
6. 禁止使用"根据提供的上下文"、"根据资料显示"等元描述性措辞，直接用【文档N】引用即可"""


class RagGraph:
    def __init__(
        self,
        llm_model:              str             = DEEPSEEK_MODEL,
        top_k:                  int             = 10,
        use_reranker:           bool            = True,
        rerank_multiplier:      int             = 3,
        rerank_score_threshold: float           = None,
        max_history_turns:      int             = 5,
    ):
        self.llm_model              = llm_model
        self.top_k                  = top_k
        self.use_reranker           = use_reranker
        self.rerank_multiplier      = rerank_multiplier
        self.rerank_score_threshold = rerank_score_threshold
        self.max_history_turns      = max_history_turns

        self._llm_client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

        embedder       = EmbeddingService()
        sparse_encoder = SparseEncoder()
        self.reranker  = RerankerService() if use_reranker else None
        self.vector_store = VectorStore(
            embedder=embedder,
            sparse_encoder=sparse_encoder,
        )

        self._conversations: dict[str, list[dict]] = {}
        self._memory = MemorySaver()
        self.graph = self._build_graph()

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        resp = self._llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.3,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        return resp.choices[0].message.content.strip()

    def _call_llm_stream(self, system_prompt: str, user_message: str):
        stream = self._llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.3,
            stream=True,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield token

    def _classify_intent(self, state: RagState) -> RagState:
        user_message = INTENT_CLASSIFY_PROMPT.format(query=state["original_query"])
        raw = self._call_llm("", user_message)
        intent = raw.strip().lower()
        if intent not in ("rag", "chat"):
            logger.warning("意图识别结果异常: %s，默认走 rag", raw)
            intent = "rag"
        logger.info("意图识别: %s → %s", state["original_query"][:50], intent)
        return {**state, "intent": intent}

    def _chat_response(self, state: RagState) -> RagState:
        history_section = self._format_history(state.get("messages", []))
        prompt = f"""## 用户问题

{state['original_query']}

{history_section}## 回答

        """
        answer = self._call_llm(CHAT_SYSTEM_PROMPT, prompt)
        return {**state, "answer": answer}

    def _chat_response_stream(self, state: RagState):
        history_section = self._format_history(state.get("messages", []))
        prompt = f"""## 用户问题

{state['original_query']}

{history_section}## 回答

        """
        for token in self._call_llm_stream(CHAT_SYSTEM_PROMPT, prompt):
            yield token

    @staticmethod
    def _route_by_intent(state: RagState) -> str:
        return state.get("intent", "rag")

    def _format_history(self, messages: list[dict]) -> str:
        if not messages:
            return ""
        parts = []
        for m in messages[-self.max_history_turns * 2:]:
            role = "用户" if m["role"] == "user" else "助手"
            parts.append(f"{role}：{m['content']}")
        return "对话历史：\n" + "\n".join(parts) + "\n\n"

    def _rewrite_question(self, state: RagState) -> RagState:
        history_section = self._format_history(state.get("messages", []))
        user_message = REWRITE_USER_PROMPT.format(
            history_section=history_section,
            query=state["original_query"],
        )
        raw = self._call_llm(REWRITE_SYSTEM_PROMPT, user_message)
        logger.info("原始查询: %s", state["original_query"])
        logger.info("重写原始输出: %s", raw)

        try:
            m = re.search(r'```json\s*(\{.*?\})\s*```', raw, re.DOTALL)
            parsed   = json.loads(m.group(1) if m else raw)
            dense_q  = parsed.get("dense_query",  "").strip()
            sparse_q = parsed.get("sparse_query", "").strip()
        except Exception:
            logger.warning("解析重写结果为 JSON 失败，降级为同一查询: %s", raw)
            dense_q = sparse_q = raw

        dense_q  = dense_q  or state["original_query"]
        sparse_q = sparse_q or state["original_query"]

        logger.info("dense_query : %s", dense_q)
        logger.info("sparse_query: %s", sparse_q)
        return {**state, "dense_query": dense_q, "sparse_query": sparse_q}

    def _retrieve(self, state: RagState) -> RagState:
        results = self.vector_store.search(
            dense_query=state["dense_query"],
            sparse_query=state["sparse_query"],
            top_k=self.top_k,
            reranker=self.reranker,
            rerank_multiplier=self.rerank_multiplier,
            rerank_score_threshold=self.rerank_score_threshold,
        )

        chunks        = [r.to_dict() for r in results]
        context_parts = []
        for i, r in enumerate(results, 1):
            heading_info = " > ".join(r.headings) if r.headings else ""
            source_info  = f"来源: {r.source_file}" if r.source_file else "来源: 未知"
            header       = f"【文档{i}】{source_info}"
            if heading_info:
                header += f" | 章节: {heading_info}"
            context_parts.append(f"{header}\n\n{r.content}")

        context = "\n\n---\n\n".join(context_parts) if context_parts else "未检索到相关内容。"
        return {**state, "retrieved_chunks": chunks, "context": context}

    def _build_prompt(self, state: RagState) -> RagState:
        history_section = self._format_history(state.get("messages", []))
        prompt = f"""## 用户问题

{state['original_query']}

{history_section}## 参考上下文

{state['context']}

## 回答

        """
        return {**state, "prompt": prompt}

    def _generate_answer(self, state: RagState) -> RagState:
        answer = self._call_llm(RAG_SYSTEM_PROMPT, state["prompt"])
        return {**state, "answer": answer}

    def _build_graph(self):
        workflow = StateGraph(RagState)

        workflow.add_node("classify_intent",   self._classify_intent)
        workflow.add_node("rewrite_question",  self._rewrite_question)
        workflow.add_node("retrieve",          self._retrieve)
        workflow.add_node("build_prompt",      self._build_prompt)
        workflow.add_node("generate_answer",   self._generate_answer)
        workflow.add_node("chat_response",     self._chat_response)

        workflow.add_edge(START,               "classify_intent")

        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {
                "rag":  "rewrite_question",
                "chat": "chat_response",
            },
        )

        workflow.add_edge("rewrite_question",  "retrieve")
        workflow.add_edge("retrieve",          "build_prompt")
        workflow.add_edge("build_prompt",      "generate_answer")
        workflow.add_edge("generate_answer",   END)
        workflow.add_edge("chat_response",     END)
        rag_graph = workflow.compile(checkpointer=self._memory)

        return rag_graph

    def stream_answer(self, query: str, thread_id: str = "default"):
        history = self._conversations.get(thread_id, [])
        state: RagState = {
            "original_query":   query,
            "intent":           "",
            "dense_query":      "",
            "sparse_query":     "",
            "retrieved_chunks": [],
            "context":          "",
            "prompt":           "",
            "answer":           "",
            "messages":         history,
        }

        state = self._classify_intent(state)
        yield ("intent", {"intent": state["intent"]})

        if state["intent"] == "chat":
            collected: list[str] = []
            for token in self._chat_response_stream(state):
                collected.append(token)
                yield ("answer_token", {"token": token})

            answer = "".join(collected)
            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": answer})
            self._conversations[thread_id] = history
            yield ("answer_done", {"answer": answer})
            return

        state = self._rewrite_question(state)
        yield ("rewrite", {"dense_query": state["dense_query"], "sparse_query": state["sparse_query"]})

        state = self._retrieve(state)
        yield ("retrieve", {"chunks": state["retrieved_chunks"]})

        state = self._build_prompt(state)
        yield ("build_prompt", {"prompt_length": len(state["prompt"])})

        collected: list[str] = []
        for token in self._call_llm_stream(RAG_SYSTEM_PROMPT, state["prompt"]):
            collected.append(token)
            yield ("answer_token", {"token": token})

        answer = "".join(collected)
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        self._conversations[thread_id] = history
        yield ("answer_done", {"answer": answer})
