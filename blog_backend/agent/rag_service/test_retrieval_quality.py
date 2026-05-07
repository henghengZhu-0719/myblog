#!/usr/bin/env python3
"""
检索效果测试脚本

流程：
1. 将每篇 test-md 文档的前半部分发送给 DeepSeek，生成 3~5 个 (dense_query, sparse_query) 对
2. 直接用这些 query 对调用 VectorStore.search()（跳过 query 改写环节）
3. 统计：源文档命中率 (Hit@k)、平均互逆排名 (MRR)、平均分数

用法：
    python test_retrieval_quality.py [--files 第一章 第二章] [--top-k 10] [--no-rerank]
"""

import argparse
import json
import logging
import os
import re
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

import sys
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from agent.rag_service.embedding_service import EmbeddingService
from agent.rag_service.vector_store import VectorStore
from agent.rag_service.reranker_service import RerankerService
from agent.rag_service.SparseEncoder_service import SparseEncoder

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DEEPSEEK_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
DEEPSEEK_MODEL = os.getenv("ANTHROPIC_MODEL", "deepseek-chat")

TEST_MD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-md")
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retrieval_reports")

QUERY_GEN_SYSTEM = """你是一名检索系统测试专家。你的任务是阅读一篇文档，根据文档内容生成用于测试检索效果的查询对。

请生成 3~5 个查询对，以 JSON 数组格式输出。每个查询对象包含：
- "dense_query": 语义丰富的自然语言查询，完整句式，用于 embedding 向量检索
- "sparse_query": 精简关键词查询（空格分隔），用于 BM25 精确关键词检索
- "expected_heading": 该查询最应该命中的章节标题
- "difficulty": "easy" | "medium" | "hard"

查询设计原则：
1. 覆盖不同难度：easy（直接出现的关键词）、medium（需要理解语义）、hard（跨章节/需要推理）
2. 多样化类型：定义类、对比类、应用类、原理类
3. dense_query 和 sparse_query 应表达同一查询意图但措辞不同
4. 查询的答案必须能在该文档中找到

输出格式（严格 JSON 数组，不要任何额外文字）：
```json
[
  {
    "dense_query": "大语言模型和传统N-gram模型有什么本质区别？",
    "sparse_query": "大语言模型 N-gram 对比 Transformer",
    "expected_heading": "3.1 语言模型与 Transformer 架构",
    "difficulty": "medium"
  }
]
```"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
@dataclass
class QueryCase:
    dense_query: str
    sparse_query: str
    expected_heading: str
    difficulty: str
    source_file: str


@dataclass
class HitResult:
    query_case: QueryCase
    hits: list = field(default_factory=list)
    source_rank: int | None = None
    source_score: float | None = None
    top1_source_match: bool = False


# ============================================================
class RetrievalTester:
    def __init__(self, top_k: int = 10, use_reranker: bool = True):
        self.top_k = top_k
        self.use_reranker = use_reranker

        self._llm = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

        embedder = EmbeddingService()
        sparse_encoder = SparseEncoder()
        reranker = RerankerService() if use_reranker else None

        self.vector_store = VectorStore(
            embedder=embedder,
            sparse_encoder=sparse_encoder,
        )
        self.reranker = reranker

    # ---- 步骤 1：让 DeepSeek 为每篇文档生成 query 对 ----

    def generate_queries_for_file(self, filepath: str, filename: str) -> list[QueryCase]:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        max_chars = 6000
        doc_snippet = content[:max_chars]
        if len(content) > max_chars:
            doc_snippet += "\n\n...(文档后续内容省略)"

        user_prompt = f"""文档名称：{filename}

文档内容：
---
{doc_snippet}
---

请根据以上文档内容生成 3~5 个测试查询对。"""

        logger.info("   🤖 正在请求 DeepSeek 生成查询...")
        resp = self._llm.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": QUERY_GEN_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        raw = resp.choices[0].message.content.strip()

        try:
            m = re.search(r"```json\s*(\[.*?\])\s*```", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group(1))
            else:
                parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("   ⚠️ JSON 解析失败，原始输出:\n%s", raw[:500])
            return []

        cases = []
        for item in parsed:
            cases.append(QueryCase(
                dense_query=item.get("dense_query", ""),
                sparse_query=item.get("sparse_query", ""),
                expected_heading=item.get("expected_heading", ""),
                difficulty=item.get("difficulty", "medium"),
                source_file=filename,
            ))
        return cases

    # ---- 步骤 2：直接调用 VectorStore.search() 测试 ----

    def search_one(self, case: QueryCase) -> HitResult:
        results = self.vector_store.search(
            dense_query=case.dense_query,
            sparse_query=case.sparse_query,
            top_k=self.top_k,
            reranker=self.reranker,
        )

        hits = [r.to_dict() for r in results]

        source_rank = None
        source_score = None
        top1_source_match = False

        for rank, r in enumerate(results, 1):
            if r.source_file == case.source_file:
                if source_rank is None:
                    source_rank = rank
                    source_score = r.score
                break

        if results and results[0].source_file == case.source_file:
            top1_source_match = True

        return HitResult(
            query_case=case,
            hits=hits,
            source_rank=source_rank,
            source_score=source_score,
            top1_source_match=top1_source_match,
        )

    # ---- 步骤 3：主流程 ----

    def run(self, file_filter: list[str] | None = None) -> list[dict]:
        all_files = sorted(
            f for f in os.listdir(TEST_MD_DIR)
            if f.endswith(".md")
        )
        if file_filter:
            all_files = [f for f in all_files if any(ff in f for ff in file_filter)]

        logger.info("📂 待测试文件: %d 个", len(all_files))

        all_queries: list[QueryCase] = []
        for filename in all_files:
            filepath = os.path.join(TEST_MD_DIR, filename)
            logger.info("📄 处理: %s", filename)
            cases = self.generate_queries_for_file(filepath, filename)
            logger.info("   ✅ 生成 %d 个查询", len(cases))
            all_queries.extend(cases)
            time.sleep(0.5)

        logger.info("\n🔍 共 %d 个查询，开始检索测试...\n", len(all_queries))

        results: list[HitResult] = []
        for i, case in enumerate(all_queries, 1):
            logger.info("[%d/%d] %s", i, len(all_queries), case.dense_query[:60])
            hit = self.search_one(case)
            results.append(hit)
            status = "✅" if hit.source_rank else "❌"
            rank_str = f"rank={hit.source_rank}" if hit.source_rank else "未命中"
            logger.info("        %s %s | score=%.4f", status, rank_str, hit.source_score or 0)

        return self._compute_metrics(results, all_queries, all_files)

    # ---- 步骤 4：计算指标并生成报告 ----

    def _compute_metrics(
        self,
        results: list[HitResult],
        all_queries: list[QueryCase],
        all_files: list[str],
    ) -> list[dict]:
        total = len(results)
        hit_any = sum(1 for r in results if r.source_rank is not None)
        hit_top1 = sum(1 for r in results if r.top1_source_match)

        reciprocal_ranks = []
        for r in results:
            if r.source_rank:
                reciprocal_ranks.append(1.0 / r.source_rank)
            else:
                reciprocal_ranks.append(0.0)

        mrr = statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0

        source_scores = [r.source_score for r in results if r.source_score is not None]
        avg_score = statistics.mean(source_scores) if source_scores else 0

        for k in [1, 3, 5, 10]:
            hit_k = sum(
                1 for r in results
                if r.source_rank is not None and r.source_rank <= k
            )
            logger.info("Hit@%d: %d/%d = %.1f%%", k, hit_k, total, hit_k / total * 100)

        logger.info("MRR: %.4f", mrr)
        logger.info("源文档平均分数: %.4f", avg_score)
        logger.info("Top-1 命中: %d/%d = %.1f%%", hit_top1, total, hit_top1 / total * 100)

        by_difficulty = {}
        for r in results:
            d = r.query_case.difficulty
            if d not in by_difficulty:
                by_difficulty[d] = {"total": 0, "hit": 0, "ranks": []}
            by_difficulty[d]["total"] += 1
            if r.source_rank:
                by_difficulty[d]["hit"] += 1
                by_difficulty[d]["ranks"].append(r.source_rank)

        logger.info("\n按难度分组的命中率:")
        for d in ["easy", "medium", "hard"]:
            if d in by_difficulty:
                stats = by_difficulty[d]
                hit_rate = stats["hit"] / stats["total"] * 100
                avg_rank = statistics.mean(stats["ranks"]) if stats["ranks"] else 0
                logger.info("  %s: %d/%d = %.1f%%  (平均排名: %.1f)", d, stats["hit"], stats["total"], hit_rate, avg_rank)

        self._write_md_report(results, all_files, mrr, by_difficulty, total, hit_any)

        return [{"case": r.query_case.__dict__, "hits": r.hits, "source_rank": r.source_rank} for r in results]

    def _write_md_report(
        self,
        results: list[HitResult],
        all_files: list[str],
        mrr: float,
        by_difficulty: dict,
        total: int,
        hit_any: int,
    ):
        os.makedirs(REPORT_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(REPORT_DIR, f"retrieval_report_{ts}.md")

        lines = []
        lines.append("# 检索效果测试报告\n")
        lines.append(f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **测试文件数**: {len(all_files)}")
        lines.append(f"- **查询总数**: {total}")
        lines.append(f"- **Top-K**: {self.top_k}")
        lines.append(f"- **Re-ranker**: {'启用 (qwen3-rerank)' if self.use_reranker else '禁用'}")
        lines.append("")

        lines.append("## 汇总指标\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        hit_any_pct = hit_any / total * 100 if total else 0
        lines.append(f"| 源文档命中率 (Hit@{self.top_k}) | {hit_any}/{total} = {hit_any_pct:.1f}% |")
        lines.append(f"| MRR (Mean Reciprocal Rank) | {mrr:.4f} |")

        for k in [1, 3, 5, 10]:
            if k > self.top_k:
                break
            hit_k = sum(1 for r in results if r.source_rank is not None and r.source_rank <= k)
            lines.append(f"| Hit@{k} | {hit_k}/{total} = {hit_k/total*100:.1f}% |")

        lines.append("")
        lines.append("## 按难度分组\n")
        lines.append("| 难度 | 命中数 | 总数 | 命中率 | 平均排名 |")
        lines.append("|------|--------|------|--------|----------|")
        for d in ["easy", "medium", "hard"]:
            if d in by_difficulty:
                s = by_difficulty[d]
                rate = s["hit"] / s["total"] * 100
                avg_rank = statistics.mean(s["ranks"]) if s["ranks"] else 0
                lines.append(f"| {d} | {s['hit']} | {s['total']} | {rate:.1f}% | {avg_rank:.1f} |")
        lines.append("")

        lines.append("## 逐查询详情\n")
        for i, r in enumerate(results, 1):
            c = r.query_case
            status = "✅" if r.source_rank else "❌"
            lines.append(f"### [{i}] {status} {c.dense_query[:80]}\n")
            lines.append(f"- **难度**: `{c.difficulty}`")
            lines.append(f"- **源文件**: `{c.source_file}`")
            lines.append(f"- **期望章节**: `{c.expected_heading}`")
            lines.append(f"- **dense_query**: {c.dense_query}")
            lines.append(f"- **sparse_query**: {c.sparse_query}")
            if r.source_rank:
                lines.append(f"- **源文档排名**: #{r.source_rank}  |  分数: {r.source_score:.4f}")
            else:
                lines.append(f"- **源文档排名**: 未命中 ❌")
            lines.append("")
            lines.append("**检索结果 (Top-{}):**".format(min(5, len(r.hits))))
            lines.append("")
            lines.append("| # | 分数 | 来源文件 | 章节 | 内容片段 |")
            lines.append("|---|------|----------|------|----------|")
            for j, h in enumerate(r.hits[:10], 1):
                src = h.get("source_file", "")
                headings = " > ".join(h.get("headings", []))
                snippet = h.get("content", "")[:80].replace("\n", " ").replace("|", "\\|")
                match_mark = " ⭐" if src == c.source_file else ""
                lines.append(f"| {j} | {h.get('score', 0):.4f} | {src}{match_mark} | {headings} | {snippet} |")
            lines.append("")
            lines.append("---\n")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info("\n📝 报告已保存至: %s", report_path)


# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检索效果测试")
    parser.add_argument("--files", nargs="*", default=None, help="指定要测试的文件名关键词，如 '第一章 第八章'")
    parser.add_argument("--top-k", type=int, default=10, help="检索返回数量 (默认 10)")
    parser.add_argument("--no-rerank", action="store_true", help="禁用 re-ranker")
    args = parser.parse_args()

    tester = RetrievalTester(
        top_k=args.top_k,
        use_reranker=not args.no_rerank,
    )

    tester.run(file_filter=args.files)
