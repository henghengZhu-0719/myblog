#!/usr/bin/env python3
"""
测试脚本：对 test-md 目录下所有 Markdown 文件进行 chunk 切分，
并展示每篇文章的 token 分布详情，同时写入 Markdown 报告。
"""

import asyncio
import os
import sys
from datetime import datetime
from io import StringIO

# ── 确保能找到 ast_parser_service ──────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ast_parser_service import MarkdownSectionParser

TEST_MD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-md")
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chunk_reports")
CHUNK_SIZE = 500
OVERLAP = 75

# 是否在报告中包含每个 chunk 的实际内容（True 时报告会比较长）
INCLUDE_CHUNK_CONTENT = True
# 每个文件最多展示多少个 chunk 的内容样本（避免报告过大）
MAX_CHUNK_SAMPLES = 10


# ============================================================
#                      报告写入器
# ============================================================

class ReportWriter:
    """同时写入控制台和 Markdown 报告文件。"""

    def __init__(self):
        self.md_buffer = StringIO()

    def console(self, text: str = ""):
        """只输出到控制台。"""
        print(text)

    def md(self, text: str = ""):
        """只写入 Markdown 报告。"""
        self.md_buffer.write(text + "\n")

    def both(self, console_text: str, md_text: str = None):
        """同时输出。md_text 为 None 时复用 console_text。"""
        print(console_text)
        self.md_buffer.write((md_text if md_text is not None else console_text) + "\n")

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.md_buffer.getvalue())
        print(f"\n✅ 报告已保存至: {filepath}")


# ============================================================
#                       工具函数
# ============================================================

def get_md_files(directory: str) -> list[str]:
    files = sorted(
        f for f in os.listdir(directory)
        if f.endswith(".md") and os.path.isfile(os.path.join(directory, f))
    )
    return files


# ============================================================
#                       核心处理
# ============================================================

async def process_one(parser: MarkdownSectionParser, filepath: str, filename: str, writer: ReportWriter):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    total_chars = len(text)
    total_tokens = parser._count_tokens(text)

    # ── 控制台输出 ──
    writer.console(f"{'=' * 70}")
    writer.console(f"  📄 {filename}")
    writer.console(f"  {'─' * 66}")
    writer.console(f"    原始文档:  {total_chars:>8} 字符  |  {total_tokens:>8} token")
    writer.console(f"  {'─' * 66}")

    chunks = await parser.parse_and_chunk(
        text=text,
        source=filename,
        chunk_size=CHUNK_SIZE,
        overlap=OVERLAP,
    )

    dist = parser.statistics(chunks, min_tokens=50, max_tokens=0, histogram_step=100)

    writer.console(f"    总 chunk  :  {dist.total_chunks}")
    writer.console(f"    总 token  :  {dist.total_tokens}")
    writer.console(f"    每 chunk token:")
    writer.console(f"      最小    :  {dist.token_min}")
    writer.console(f"      最大    :  {dist.token_max}")
    writer.console(f"      平均    :  {dist.token_mean:.1f}")
    writer.console(f"      中位数  :  {dist.token_median:.0f}")
    writer.console(f"      P25     :  {dist.token_p25:.0f}")
    writer.console(f"      P75     :  {dist.token_p75:.0f}")
    writer.console(f"      P95     :  {dist.token_p95:.0f}")
    writer.console(f"      标准差  :  {dist.token_stddev:.1f}")
    writer.console(f"  内容类型分布:")
    for t, count in sorted(dist.type_counts.items()):
        pct = count / dist.total_chunks * 100
        writer.console(f"      {t:<15}: {count:>3}  ({pct:5.1f}%)")
    writer.console(f"  问题 chunk:")
    writer.console(f"      空 chunk     : {len(dist.empty_chunks)}")
    writer.console(f"      过小 chunk   : {len(dist.too_small_chunks)}")
    writer.console(f"      过大 chunk   : {len(dist.too_large_chunks)}")
    writer.console(f"      孤立 chunk   : {len(dist.orphan_chunks)}")

    if dist.histogram:
        writer.console(f"  Token 直方图:")
        for bucket, count in dist.histogram.items():
            bar = "█" * min(count, 50)
            writer.console(f"      {bucket:<12}: {count:>3}  {bar}")

    writer.console()

    # ── Markdown 报告输出 ──
    writer.md(f"## 📄 {filename}\n")
    writer.md(f"### 基本信息\n")
    writer.md(f"| 指标 | 值 |")
    writer.md(f"|------|-----|")
    writer.md(f"| 原始字符数 | {total_chars:,} |")
    writer.md(f"| 原始 Token 数 | {total_tokens:,} |")
    writer.md(f"| 总 chunk 数 | {dist.total_chunks} |")
    writer.md(f"| 总 token 数 | {dist.total_tokens:,} |")
    writer.md("")

    writer.md(f"### Token 分布\n")
    writer.md(f"| 统计量 | 值 |")
    writer.md(f"|--------|-----|")
    writer.md(f"| 最小 | {dist.token_min} |")
    writer.md(f"| 最大 | {dist.token_max} |")
    writer.md(f"| 平均 | {dist.token_mean:.1f} |")
    writer.md(f"| 中位数 (P50) | {dist.token_median:.0f} |")
    writer.md(f"| P25 | {dist.token_p25:.0f} |")
    writer.md(f"| P75 | {dist.token_p75:.0f} |")
    writer.md(f"| P95 | {dist.token_p95:.0f} |")
    writer.md(f"| 标准差 | {dist.token_stddev:.1f} |")
    writer.md("")

    writer.md(f"### 内容类型分布\n")
    writer.md(f"| 类型 | 数量 | 占比 |")
    writer.md(f"|------|------|------|")
    for t, count in sorted(dist.type_counts.items()):
        pct = count / dist.total_chunks * 100
        writer.md(f"| {t} | {count} | {pct:.1f}% |")
    writer.md("")

    writer.md(f"### 问题 chunk 检查\n")
    writer.md(f"| 类别 | 数量 |")
    writer.md(f"|------|------|")
    writer.md(f"| 空 chunk | {len(dist.empty_chunks)} |")
    writer.md(f"| 过小 chunk (<50 token) | {len(dist.too_small_chunks)} |")
    writer.md(f"| 过大 chunk | {len(dist.too_large_chunks)} |")
    writer.md(f"| 孤立 chunk | {len(dist.orphan_chunks)} |")
    writer.md("")

    if dist.histogram:
        writer.md(f"### Token 直方图\n")
        writer.md("```")
        for bucket, count in dist.histogram.items():
            bar = "█" * min(count, 50)
            writer.md(f"  {bucket:<12}: {count:>3}  {bar}")
        writer.md("```\n")

    # ── chunk 内容样本 ──
    if INCLUDE_CHUNK_CONTENT and chunks:
        writer.md(f"### Chunk 内容样本\n")
        sample_count = min(MAX_CHUNK_SAMPLES, len(chunks))
        writer.md(f"> 共 {len(chunks)} 个 chunk，展示前 {sample_count} 个：\n")

        for i, chunk in enumerate(chunks[:sample_count], 1):
            content = getattr(chunk, "content", None) or getattr(chunk, "text", "") or str(chunk)
            tokens = parser._count_tokens(content) if content else 0
            chunk_type = getattr(chunk, "type", getattr(chunk, "chunk_type", "unknown"))
            headings = getattr(chunk, "headings", None)

            writer.md(f"<details>")
            writer.md(f"<summary><b>Chunk #{i}</b> | type: <code>{chunk_type}</code> | tokens: {tokens}"
                      + (f" | path: {' > '.join(headings)}" if headings else "")
                      + "</summary>\n")
            writer.md("```markdown")
            # 截断过长内容（避免单 chunk 撑爆报告）
            preview = content if len(content) <= 2000 else content[:2000] + "\n...(已截断)"
            writer.md(preview)
            writer.md("```")
            writer.md("</details>\n")

    writer.md("---\n")

    return chunks, dist


# ============================================================
#                          主流程
# ============================================================

async def main():
    parser = MarkdownSectionParser(chunk_size=CHUNK_SIZE, overlap=OVERLAP)
    writer = ReportWriter()

    files = get_md_files(TEST_MD_DIR)
    if not files:
        print(f"在 {TEST_MD_DIR} 下未找到 .md 文件")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"chunk_report_{timestamp}.md"
    report_path = os.path.join(REPORT_DIR, report_filename)

    # ── 报告头部 ──
    writer.md(f"# Markdown Chunk 切分报告\n")
    writer.md(f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    writer.md(f"- **测试目录**: `{TEST_MD_DIR}`")
    writer.md(f"- **chunk_size**: {CHUNK_SIZE}")
    writer.md(f"- **overlap**: {OVERLAP}")
    writer.md(f"- **文件数量**: {len(files)}\n")
    writer.md("---\n")

    print(f"  ✅ 共发现 {len(files)} 个 Markdown 文件\n")

    all_stats = []
    for filename in files:
        filepath = os.path.join(TEST_MD_DIR, filename)
        chunks, dist = await process_one(parser, filepath, filename, writer)
        all_stats.append((filename, chunks, dist))

    # ── 汇总对比（控制台）──
    print(f"{'=' * 70}")
    print(f"  📊 所有文章汇总对比")
    print(f"{'=' * 70}")
    header = f"  {'文章':<28} {'chunk数':>6} {'总tokens':>9} {'平均token':>9} {'P50':>6} {'P95':>6}"
    print(header)
    print(f"  {'─' * 66}")
    total_chunks = 0
    total_tokens = 0
    for filename, chunks, dist in all_stats:
        short = filename.replace(".md", "")
        short = short[:28]
        print(f"  {short:<28} {dist.total_chunks:>6} {dist.total_tokens:>9} "
              f"{dist.token_mean:>9.1f} {dist.token_median:>6.0f} {dist.token_p95:>6.0f}")
        total_chunks += dist.total_chunks
        total_tokens += dist.total_tokens
    print(f"  {'─' * 66}")
    print(f"  {'总计':<28} {total_chunks:>6} {total_tokens:>9}")

    # ── 汇总对比（Markdown）──
    writer.md(f"## 📊 所有文章汇总对比\n")
    writer.md(f"| 文章 | chunk 数 | 总 tokens | 平均 token | P50 | P95 |")
    writer.md(f"|------|---------:|----------:|-----------:|----:|----:|")
    for filename, chunks, dist in all_stats:
        short = filename.replace(".md", "")
        writer.md(f"| {short} | {dist.total_chunks} | {dist.total_tokens:,} | "
                  f"{dist.token_mean:.1f} | {dist.token_median:.0f} | {dist.token_p95:.0f} |")
    writer.md(f"| **总计** | **{total_chunks}** | **{total_tokens:,}** | - | - | - |\n")

    # ── 全局统计 ──
    if all_stats:
        avg_chunks_per_file = total_chunks / len(all_stats)
        avg_tokens_per_chunk = total_tokens / total_chunks if total_chunks else 0
        writer.md(f"### 全局统计\n")
        writer.md(f"- **文件总数**: {len(all_stats)}")
        writer.md(f"- **chunk 总数**: {total_chunks}")
        writer.md(f"- **token 总数**: {total_tokens:,}")
        writer.md(f"- **平均每文件 chunk 数**: {avg_chunks_per_file:.1f}")
        writer.md(f"- **平均每 chunk token 数**: {avg_tokens_per_chunk:.1f}")

    # ── 写入文件 ──
    writer.save(report_path)


if __name__ == "__main__":
    asyncio.run(main())
