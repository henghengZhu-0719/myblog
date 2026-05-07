import asyncio
import os
import re
import logging
from dataclasses import dataclass, field
from enum import Flag, auto
from markdown_it import MarkdownIt
from typing import Optional

import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
VISION_MODEL = "qwen-vl-max"

DEEPSEEK_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
DEEPSEEK_MODEL = os.getenv("ANTHROPIC_MODEL")

_client = AsyncOpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=DASHSCOPE_BASE_URL,
)

_deepseek_client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
) if DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL else _client


# ------------------------------------------------------------------
# 数据结构
# ------------------------------------------------------------------
from dataclasses import dataclass, field
import statistics as stats_lib   # 标准库

@dataclass
class ChunkDistribution:
    # ── 总量 ──────────────────────────────────────────
    total_chunks:   int = 0
    total_tokens:   int = 0
    total_chars:    int = 0

    # ── token 分布 ────────────────────────────────────
    token_min:      int = 0
    token_max:      int = 0
    token_mean:     float = 0.0
    token_median:   float = 0.0
    token_p25:      float = 0.0   # 25 分位
    token_p75:      float = 0.0   # 75 分位
    token_p95:      float = 0.0   # 95 分位，超大 chunk 预警线
    token_stddev:   float = 0.0

    # ── 内容类型分布 ──────────────────────────────────
    type_counts: dict[str, int] = field(default_factory=dict)

    # ── 问题 chunk ────────────────────────────────────
    empty_chunks:      list[int] = field(default_factory=list)   # chunk_index 列表
    too_small_chunks:  list[int] = field(default_factory=list)   # token < min_threshold
    too_large_chunks:  list[int] = field(default_factory=list)   # token > max_threshold
    orphan_chunks:     list[int] = field(default_factory=list)   # 无 headings_path

    # ── token 分桶直方图 ──────────────────────────────
    histogram: dict[str, int] = field(default_factory=dict)      # "0-50": 3, "50-100": 12 ...

    def __str__(self) -> str:
        lines = [
            "=" * 55,
            "  Chunk 分布统计报告",
            "=" * 55,
            f"  总 chunk 数   : {self.total_chunks}",
            f"  总 token 数   : {self.total_tokens}",
            f"  总字符数      : {self.total_chars}",
            "",
            "── Token 分布 ──────────────────────────────",
            f"  min / max     : {self.token_min} / {self.token_max}",
            f"  mean / median : {self.token_mean:.1f} / {self.token_median:.1f}",
            f"  p25 / p75     : {self.token_p25:.1f} / {self.token_p75:.1f}",
            f"  p95           : {self.token_p95:.1f}",
            f"  stddev        : {self.token_stddev:.1f}",
            "",
            "── 内容类型分布 ─────────────────────────────",
        ]
        for t, count in sorted(self.type_counts.items()):
            bar = "█" * min(count, 40)
            lines.append(f"  {t:<10}: {count:>4}  {bar}")

        lines += [
            "",
            "── Token 直方图 ─────────────────────────────",
        ]
        for bucket, count in self.histogram.items():
            bar = "█" * min(count, 40)
            lines.append(f"  {bucket:<12}: {count:>4}  {bar}")

        lines += [
            "",
            "── 问题 Chunk ───────────────────────────────",
            f"  空 chunk       : {len(self.empty_chunks)}  {self.empty_chunks}",
            f"  过小 chunk     : {len(self.too_small_chunks)}  {self.too_small_chunks}",
            f"  过大 chunk     : {len(self.too_large_chunks)}  {self.too_large_chunks}",
            f"  孤立 chunk     : {len(self.orphan_chunks)}  {self.orphan_chunks}",
            "=" * 55,
        ]
        return "\n".join(lines)


class ContentType(Flag):
    TEXT  = auto()
    CODE  = auto()
    TABLE = auto()
    IMAGE = auto()
    MATH  = auto()


@dataclass
class Section:
    level: int
    heading: str
    content: str
    headings: list[str] = field(default_factory=list)
    content_types: ContentType = ContentType.TEXT
    token_count: int = 0
    line_start: int = 0
    line_end: int = 0
    raw_code_blocks: list[str] = field(default_factory=list)

@dataclass
class ChunkMetadata:
    # 来源信息
    source: str                          # 来源文件名，如 "agent_intro.md"
    chunk_index: int                     # 在文档中的顺序

    # 结构信息
    headings_path: list[str] = field(default_factory=list)  # ['第一章', '1.1 什么是智能体']
    section_level: int = 0               # 所在标题层级，H1=1, H2=2，顶层=0

    # 内容类型标签
    content_types: ContentType   = ContentType.TEXT

    # 位置信息（用于溯源）
    line_start: int = 0
    line_end: int = 0

    # 大小信息（用于 Context Window 管理）
    char_count: int = 0
    token_count: int = 0

    # 上下文链（用于召回后扩展窗口）
    prev_chunk_index: Optional[int] = None
    next_chunk_index: Optional[int] = None

    # 原始代码内容（召回时保留完整代码供 LLM 使用）
    raw_code: str = ""
    # bool 全部派生，永远与 content_types 同步
    @property
    def has_code(self)  -> bool: return ContentType.CODE  in self.content_types
    @property
    def has_image(self) -> bool: return ContentType.IMAGE in self.content_types
    @property
    def has_table(self) -> bool: return ContentType.TABLE in self.content_types
    @property
    def has_math(self)  -> bool: return ContentType.MATH  in self.content_types

@dataclass
class Chunk:
    content: str
    metadata: ChunkMetadata

    @property
    def headings(self) -> list[str]:
        return self.metadata.headings_path


# ------------------------------------------------------------------
# AST-based Section 解析器
# ------------------------------------------------------------------

class MarkdownSectionParser:

    def __init__(self, chunk_size: int = 500, overlap: int = 75, max_concurrent_api: int = 5):
        self._md = MarkdownIt().enable("table")
        self._TOKENIZER = tiktoken.get_encoding("cl100k_base")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._semaphore = asyncio.Semaphore(max_concurrent_api)
    
    async def parse_and_chunk(
        self,
        text: str,
        source: str = "",
        chunk_size: int = 0,
        overlap: int = 0,
    ) -> list[Chunk]:
        """
        一站式入口：parse → enrich → chunk，返回最终 Chunk 列表。

        Args:
            text:       原始 Markdown 文本
            source:     来源文件名，写入 ChunkMetadata.source
            chunk_size: 覆盖默认值（0 = 使用构造时的 self.chunk_size）
            overlap:    覆盖默认值（0 = 使用构造时的 self.overlap）
        """
        sections = self.parse(text)
        enriched = await self.enrich_sections(sections)
        chunks   = self.split_markdown_into_chunks(enriched, chunk_size, overlap)

        if source:
            for chunk in chunks:
                chunk.metadata.source = source

        return chunks


    def parse(self, text: str
    ) -> list[Section]:
        """
        将 Markdown 文本解析为 Section 列表（叶子内容模式）。
        每个 Section 的 content 只包含该标题到下一个标题之间的直接正文。
        
        策略：通过 heading_open token 的行号直接切分原始文本，
              不受 inline token map 信息不可靠的影响。
        """
        tokens = self._md.parse(text)
        lines = text.splitlines()
        sections: list[Section] = []
        heading_stack: list[tuple[int, str]] = []

        # ── Pass 1：扫描所有标题位置 ──────────────────────────
        heading_positions: list[dict] = []  # {line, level, heading, headings}

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type == "heading_open":
                level = int(token.tag[1])
                line = token.map[0] if token.map else 0

                # 读取标题文字（下一个 token 是 inline）
                heading_text = ""
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    heading_text = self._extract_plain_text(tokens[i + 1])

                # 更新标题路径栈
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, heading_text))

                heading_positions.append({
                    "line": line,
                    "level": level,
                    "heading": heading_text,
                    "headings": [h for _, h in heading_stack],
                })

                i += 2
                continue
            i += 1

        if not heading_positions:
            # 没有任何标题，整篇文档作为一个 section
            content = text.strip()
            if content:
                sections.append(Section(
                    level=0, heading="", content=content,
                    headings=[], content_types=self._detect_content_types(content),
                    token_count=self._count_tokens(content),
                    line_start=0, line_end=len(lines),
                ))
            return sections

        # ── Pass 2：按行号区间提取内容 ─────────────────────────
        # 文档开头（第一个标题之前）
        pre_end = heading_positions[0]["line"]
        if pre_end > 0:
            pre_content = "\n".join(lines[0:pre_end]).strip()
            if pre_content:
                sections.append(Section(
                    level=0, heading="", content=self._clean_content(pre_content),
                    headings=[],
                    content_types=self._detect_content_types(pre_content),
                    token_count=self._count_tokens(pre_content),
                    line_start=0, line_end=pre_end,
                ))

        # 每个标题到下一个标题之间的正文
        for idx, pos in enumerate(heading_positions):
            content_start = pos["line"] + 1  # 标题行之后
            content_end = heading_positions[idx + 1]["line"] if idx + 1 < len(heading_positions) else len(lines)
            content = "\n".join(lines[content_start:content_end]).strip()

            # 先检测内容类型（基于原始文本），再清洗 HTML
            content_types = self._detect_content_types(content)
            content = self._clean_content(content)

            sections.append(Section(
                level=pos["level"],
                heading=pos["heading"],
                content=content,
                headings=pos["headings"],
                content_types=content_types,
                token_count=self._count_tokens(content),
                line_start=pos["line"],
                line_end=content_end,
            ))

        return sections


    def _count_tokens(self, text: str
    ) -> int:
        return len(self._TOKENIZER.encode(text))

    # ------------------------------------------------------------------
    # Chunk 切分
    # ------------------------------------------------------------------

    def split_markdown_into_chunks(
        self, sections: list[Section], chunk_size: int = 0, overlap: int = 0) -> list[Chunk]:
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.overlap

        sections = self._merge_small_sections(sections, chunk_size)
        chunks: list[Chunk] = []
        for section in sections:
            chunks.extend(self._split_section(section, chunk_size))
        for i, chunk in enumerate(chunks):
            chunk.metadata.chunk_index = i
        chunks = self._apply_overlap(chunks, overlap)
        return chunks

    def _merge_small_sections(self, sections: list[Section], chunk_size: int) -> list[Section]:
        """同父 + 不含代码/表格 + 合并后不超限 → 合并"""
        if not sections:
            return []
        merged = [sections[0]]
        for sec in sections[1:]:
            last = merged[-1]
            same_parent = last.headings[:-1] == sec.headings[:-1] and last.level == sec.level
            has_complex = (
                ContentType.CODE in last.content_types
                or ContentType.TABLE in last.content_types
                or ContentType.CODE in sec.content_types
                or ContentType.TABLE in sec.content_types
            )
            merged_token = last.token_count + sec.token_count
            if same_parent and not has_complex and merged_token <= chunk_size:
                merged[-1] = Section(
                    level=last.level,
                    heading=last.heading,
                    content=last.content + "\n\n" + sec.content,
                    headings=last.headings,
                    content_types=last.content_types | sec.content_types,
                    token_count=merged_token,
                    line_start=last.line_start,
                    line_end=sec.line_end,
                    raw_code_blocks=last.raw_code_blocks + sec.raw_code_blocks,
                )
            else:
                merged.append(sec)
        return merged

    def _split_section(self, section: Section, chunk_size: int) -> list[Chunk]:
        """≤ chunk_size 直接打包，否则按段落→句子→force_split 逐级切分"""
        if section.token_count <= chunk_size:
            return [self._build_chunk(section, [section.content], 0)]

        paragraphs = re.split(r'\n\n+', section.content)
        chunks: list[Chunk] = []
        current_parts: list[str] = []
        current_token = 0
        chunk_index = 0

        def flush():
            nonlocal chunk_index
            if current_parts:
                chunks.append(self._build_chunk(section, current_parts, chunk_index))
                chunk_index += 1
            current_parts.clear()
            nonlocal current_token
            current_token = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)
            if para_tokens == 0:
                continue
            if para_tokens > chunk_size:
                flush()
                # 句子级切分
                sentences = re.split(r'(?<=[。！？.!?])\s+', para)
                for sentence in sentences:
                    sent_tokens = self._count_tokens(sentence)
                    if sent_tokens == 0:
                        continue
                    if sent_tokens > chunk_size:
                        flush()
                        for part in self._force_split(sentence, chunk_size):
                            chunks.append(self._build_chunk(section, [part], chunk_index))
                            chunk_index += 1
                    else:
                        if current_token + sent_tokens > chunk_size:
                            flush()
                        current_parts.append(sentence)
                        current_token += sent_tokens
            else:
                if current_token + para_tokens > chunk_size:
                    flush()
                current_parts.append(para)
                current_token += para_tokens

        flush()
        return chunks

    def _force_split(self, text: str, chunk_size: int) -> list[str]:
        """超长文本按 token 数强行截断"""
        tokens = self._TOKENIZER.encode(text)
        parts: list[str] = []
        for i in range(0, len(tokens), chunk_size):
            parts.append(self._TOKENIZER.decode(tokens[i : i + chunk_size]))
        return parts

    def _build_chunk(self, section: Section, parts: list[str], chunk_index: int) -> Chunk:
        content = "\n\n".join(parts)
        token_count = self._count_tokens(content)
        return Chunk(
            content=content,
            metadata=ChunkMetadata(
                source="",
                chunk_index=chunk_index,
                headings_path=section.headings,
                section_level=section.level,
                content_types=section.content_types,
                char_count=len(content),
                token_count=token_count,
                line_start=section.line_start,
                line_end=section.line_end,
                raw_code="\n\n".join(section.raw_code_blocks),
            ),
        )

    def _apply_overlap(self, chunks: list[Chunk], overlap: int) -> list[Chunk]:
        """前一个 chunk 末尾 overlap 个 token 追加到当前 chunk 开头，同时写入 prev/next_chunk_index"""
        if overlap <= 0 or len(chunks) <= 1:
            for i, c in enumerate(chunks):
                c.metadata.prev_chunk_index = i - 1 if i > 0 else None
                c.metadata.next_chunk_index = i + 1 if i < len(chunks) - 1 else None
            return chunks

        result: list[Chunk] = []
        for i, chunk in enumerate(chunks):
            content = chunk.content
            if i > 0:
                prev_text = chunks[i - 1].content
                paragraphs = re.split(r'\n\n+', prev_text.strip())
                selected: list[str] = []
                selected_token = 0
                for para in reversed(paragraphs):
                    para_token = self._count_tokens(para)
                    if not selected and para_token > overlap:
                        sentences = re.split(r'(?<=[。！？.!?])\s+', para)
                        sent_selected: list[str] = []
                        sent_selected_token = 0
                        for sent in reversed(sentences):
                            sent_t = self._count_tokens(sent)
                            if sent_selected and sent_selected_token + sent_t > overlap:
                                break
                            sent_selected.insert(0, sent)
                            sent_selected_token += sent_t
                        if sent_selected:
                            selected.append("".join(sent_selected))
                        else:
                            selected.append(self._TOKENIZER.decode(self._TOKENIZER.encode(para)[-overlap:]))
                        break
                    if selected_token + para_token > overlap:
                        break
                    selected.insert(0, para)
                    selected_token += para_token
                if selected:
                    content = "\n\n".join(selected) + "\n\n" + content

            metadata = ChunkMetadata(
                source=chunk.metadata.source,
                chunk_index=chunk.metadata.chunk_index,
                headings_path=chunk.metadata.headings_path,
                section_level=chunk.metadata.section_level,
                content_types=chunk.metadata.content_types,
                char_count=len(content),
                token_count=self._count_tokens(content),
                line_start=chunk.metadata.line_start,
                line_end=chunk.metadata.line_end,
                prev_chunk_index=i - 1 if i > 0 else None,
                next_chunk_index=i + 1 if i < len(chunks) - 1 else None,
                raw_code=chunk.metadata.raw_code,
            )
            result.append(Chunk(content=content, metadata=metadata))

        return result

    # ------------------------------------------------------------------
    # 内容类型检测：直接看 token.type，不需要正则
    # ------------------------------------------------------------------

    def _detect_content_types(self, content_text: str) -> ContentType:
        types = ContentType.TEXT

        # 直接基于文本正则检测
        if re.search(r'```[\s\S]*?```', content_text):
            types |= ContentType.CODE
        if re.search(r'^\|.+\|(?:\n\|[-:| ]+\|)*', content_text, re.MULTILINE):
            types |= ContentType.TABLE
        if re.search(r'\$\$[\s\S]*?\$\$', content_text):
            types |= ContentType.MATH
        if re.search(r'\$[^\$]+\$', content_text):
            types |= ContentType.MATH
        if re.search(r'<img\s[^>]*src=|<img[^>]*/>', content_text, re.IGNORECASE):
            types |= ContentType.IMAGE
        if re.search(r'!\[.*?\]\(.*?\)', content_text):
            types |= ContentType.IMAGE

        return types

    # ------------------------------------------------------------------
    # 提取标题纯文本（去除加粗、斜体等内联标记）
    # ------------------------------------------------------------------

    def _extract_plain_text(self, inline_token) -> str:
        if not inline_token.children:
            return inline_token.content or ""
        return "".join(
            child.content
            for child in inline_token.children
            if child.type == "text" or child.type == "code_inline"
        ).strip()

    def _clean_content(self, text: str) -> str:
        protected = []

        def protect(match):
            protected.append(match.group())
            return f"__PROTECTED_{len(protected) - 1}__"

        # 1. 保护代码块和数学块（顺序很重要：先保护，再清洗）
        text = re.sub(r'```[\s\S]*?```', protect, text)
        text = re.sub(r'\$\$[\s\S]*?\$\$', protect, text)

        # 2. HTML 图片 → 标准 Markdown 图片
        text = re.sub(
            r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']+)["\'][^>]*\s*/?>',
            r'![\2](\1)', text
        )
        text = re.sub(
            r'<img\s+[^>]*alt=["\']([^"\']+)["\'][^>]*src=["\']([^"\']+)["\'][^>]*\s*/?>',
            r'![\1](\2)', text
        )
        text = re.sub(
            r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*\s*/?>',
            r'![图片](\1)', text
        )

        # 3. <strong>/<em> → Markdown 语法
        text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
        text = re.sub(r'<em>(.*?)</em>',         r'*\1*',   text, flags=re.DOTALL)

        # 4. 纯布局标签：删标签保内容
        for tag in ['div', 'p', 'br', 'span', 'center', 'section']:
            text = re.sub(rf'<{tag}[^>]*>', '', text)
            text = re.sub(rf'</{tag}>', '', text)

        # 5. 统一还原所有被保护的块
        for i, block in enumerate(protected):
            text = text.replace(f"__PROTECTED_{i}__", block)

        # 6. 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        return text

    
    async def enrich_sections(self, sections: list[Section]) -> list[Section]:
        """对每个 section 的特殊内容进行语义增强，并发调用模型，单个失败不影响其余"""
        tasks = [self._enrich_section(sec) for sec in sections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        enriched: list[Section] = []
        for sec, result in zip(sections, results):
            if isinstance(result, Exception):
                logger.warning("Section 增强失败 (%s): %s", sec.heading or "(无标题)", result)
                enriched.append(sec)
            else:
                enriched.append(result)
        return enriched


    async def _enrich_section(self, section: Section) -> Section:
        content = section.content
        raw_code_blocks: list[str] = []

        if ContentType.IMAGE in section.content_types:
            content = await self._replace_images(content)

        if ContentType.CODE in section.content_types:
            raw_code_blocks = re.findall(r'```[\s\S]*?```', content)
            content = await self._replace_code_blocks(content)

        # TABLE 保留原始 Markdown，不处理

        # 重新计算 token（内容已变）
        new_token_count = self._count_tokens(content)

        return Section(
            level=section.level,
            heading=section.heading,
            content=content,
            headings=section.headings,
            content_types=section.content_types,
            token_count=new_token_count,
            line_start=section.line_start,
            line_end=section.line_end,
            raw_code_blocks=raw_code_blocks,
        )


    async def _replace_images(self, content: str) -> str:
        """将 ![alt](url) 替换为视觉模型生成的语义描述，并发调用"""
        matches = list(re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content))
        if not matches:
            return content
        tasks = [self._vision_summary(m.group(2), m.group(1)) for m in matches]
        descriptions = await asyncio.gather(*tasks)
        parts = []
        cursor = 0
        for match, desc in zip(matches, descriptions):
            parts.append(content[cursor : match.start()])
            parts.append(f"[图片描述：{desc}]")
            cursor = match.end()
        parts.append(content[cursor:])
        return "".join(parts)


    async def _replace_code_blocks(self, content: str) -> str:
        """将 ```code``` 替换为 LLM 生成的代码摘要，并发调用"""
        matches = list(re.finditer(r'```[\s\S]*?```', content))
        if not matches:
            return content
        tasks = [self._code_summary(m.group(0)) for m in matches]
        summaries = await asyncio.gather(*tasks)
        parts = []
        cursor = 0
        for match, summary in zip(matches, summaries):
            parts.append(content[cursor : match.start()])
            parts.append(f"[代码摘要：{summary}]")
            cursor = match.end()
        parts.append(content[cursor:])
        return "".join(parts)

    async def _vision_summary(self, url: str, alt: str) -> str:
        """调用阿里云通义千问VL视觉模型，返回图片语义描述"""
        async with self._semaphore:
            try:
                prompt = f"请详细描述这张图片的内容，不超过80个字，不要分点，不要重复标题。图片的alt标签为：{alt}" if alt else "请详细描述这张图片的内容，不超过80个字"
                image_url = await self._resolve_image_url(url)
                response = await _client.chat.completions.create(
                    model=VISION_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": image_url}},
                            ],
                        }
                    ],
                    max_tokens=512,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("视觉模型调用失败（url=%s）: %s", url, e)
                return f"[图片：{alt}]" if alt else "[图片]"

    async def _resolve_image_url(self, url: str) -> str:
        """将图片路径转为DashScope可接受的URL格式，支持网络URL、data URI和本地路径"""
        if url.startswith("data:"):
            return url
        import base64, mimetypes
        if url.startswith(("http://", "https://")):
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.content
                mime_type = resp.headers.get("content-type", "image/png")
        else:
            mime_type, _ = mimetypes.guess_type(url)
            if not mime_type:
                mime_type = "image/png"
            loop = asyncio.get_running_loop()
            with open(url, "rb") as f:
                data = await loop.run_in_executor(None, f.read)
        return f"data:{mime_type};base64,{base64.b64encode(data).decode('utf-8')}"


    async def _code_summary(self, code: str) -> str:
        """调用 DeepSeek 模型，返回代码功能摘要"""
        async with self._semaphore:
            try:
                response = await _deepseek_client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": f"请用一句话简要总结以下代码的核心功能，不超过100个字：\n\n{code}",
                        }
                    ],
                    stream=False,
                    temperature=0.3,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("代码摘要模型调用失败: %s", e)
                return "[代码块]"
    
    def statistics(
        self,
        chunks: list[Chunk],
        min_tokens: int = 50,          # 低于此值 → too_small
        max_tokens: int = 0,           # 高于此值 → too_large（0 = chunk_size * 1.2）
        histogram_step: int = 100,     # 直方图桶宽
    ) -> ChunkDistribution:
        """
        分析 chunk 列表的 token 分布，返回 ChunkDistribution。
        直接 print(result) 可看到格式化报告。
        """
        if not chunks:
            return ChunkDistribution()

        max_tokens = max_tokens or int(self.chunk_size * 1.2)
        token_counts = [c.metadata.token_count for c in chunks]

        # ── 分位数计算 ────────────────────────────────────
        sorted_tokens = sorted(token_counts)
        n = len(sorted_tokens)

        def percentile(p: float) -> float:
            idx = (n - 1) * p
            lo, hi = int(idx), min(int(idx) + 1, n - 1)
            return sorted_tokens[lo] + (sorted_tokens[hi] - sorted_tokens[lo]) * (idx - lo)

        # ── 内容类型分布 ──────────────────────────────────
        type_counts: dict[str, int] = {}
        for chunk in chunks:
            ct = chunk.metadata.content_types
            label_parts = []
            if ContentType.TEXT  in ct: label_parts.append("TEXT")
            if ContentType.CODE  in ct: label_parts.append("CODE")
            if ContentType.TABLE in ct: label_parts.append("TABLE")
            if ContentType.IMAGE in ct: label_parts.append("IMAGE")
            if ContentType.MATH  in ct: label_parts.append("MATH")
            label = "+".join(label_parts) or "UNKNOWN"
            type_counts[label] = type_counts.get(label, 0) + 1

        # ── 直方图分桶 ────────────────────────────────────
        histogram: dict[str, int] = {}
        for t in token_counts:
            bucket_start = (t // histogram_step) * histogram_step
            bucket_end   = bucket_start + histogram_step
            key = f"{bucket_start}-{bucket_end}"
            histogram[key] = histogram.get(key, 0) + 1
        # 按桶起始值排序
        histogram = dict(sorted(histogram.items(), key=lambda x: int(x[0].split("-")[0])))

        # ── 问题 chunk 检测 ───────────────────────────────
        empty_chunks     = [c.metadata.chunk_index for c in chunks if c.metadata.token_count == 0]
        too_small_chunks = [c.metadata.chunk_index for c in chunks if 0 < c.metadata.token_count < min_tokens]
        too_large_chunks = [c.metadata.chunk_index for c in chunks if c.metadata.token_count > max_tokens]
        orphan_chunks    = [c.metadata.chunk_index for c in chunks if not c.metadata.headings_path]

        return ChunkDistribution(
            total_chunks  = n,
            total_tokens  = sum(token_counts),
            total_chars   = sum(c.metadata.char_count for c in chunks),
            token_min     = sorted_tokens[0],
            token_max     = sorted_tokens[-1],
            token_mean    = stats_lib.mean(token_counts),
            token_median  = stats_lib.median(token_counts),
            token_p25     = percentile(0.25),
            token_p75     = percentile(0.75),
            token_p95     = percentile(0.95),
            token_stddev  = stats_lib.stdev(token_counts) if n > 1 else 0.0,
            type_counts   = type_counts,
            histogram     = histogram,
            empty_chunks     = empty_chunks,
            too_small_chunks = too_small_chunks,
            too_large_chunks = too_large_chunks,
            orphan_chunks    = orphan_chunks,
        )




if __name__ == "__main__":
    ## 测试用文件
    with open("/Users/zhuyq/hello-agents/docs/chapter1/第一章初识智能体.md", "r", encoding="utf-8") as f:
        SAMPLE_MD = f.read()


    async def main():
        parser = MarkdownSectionParser()
        chunks = await parser.parse_and_chunk(text=SAMPLE_MD, source="第一章初识智能体.md", chunk_size=500, overlap=75)
        print("=" * 80)
        print(f"3. Chunks（共 {len(chunks)} 个，chunk_size=500, overlap=75）")
        print("=" * 80)
        for i, chunk in enumerate(chunks):
            m = chunk.metadata
            print(f"{'=' * 80}")
            print(f"【Chunk {i}】token={m.token_count:>4}  "
                  f"headings={' > '.join(m.headings_path) if m.headings_path else '(无)'}")
            print(f"    prev={m.prev_chunk_index}  next={m.next_chunk_index}  "
                  f"types={m.content_types}  lines={m.line_start}-{m.line_end}")
            print(f"    content:")
            print(chunk.content.strip())
            print(f"    raw_code:")
            print(m.raw_code)


    asyncio.run(main())


