import asyncio
import base64
import logging
import mimetypes
import os
import re
import statistics as stats_lib

import httpx
import tiktoken
from markdown_it import MarkdownIt
from openai import AsyncOpenAI

from agent.rag.config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    VISION_MODEL,
)
from agent.rag.models.chunk import (
    Chunk,
    ChunkMetadata,
    ChunkDistribution,
    ContentType,
    Section,
)

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
_deepseek_client = (
    AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    if DEEPSEEK_API_KEY and DEEPSEEK_BASE_URL
    else _client
)


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
        sections = self.parse(text)
        enriched = await self.enrich_sections(sections)
        chunks   = self.split_markdown_into_chunks(enriched, chunk_size, overlap)
        if source:
            for chunk in chunks:
                chunk.metadata.source = source
        return chunks

    def parse(self, text: str) -> list[Section]:
        tokens = self._md.parse(text)
        lines = text.splitlines()
        sections: list[Section] = []
        heading_stack: list[tuple[int, str]] = []
        heading_positions: list[dict] = []

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.type == "heading_open":
                level = int(token.tag[1])
                line = token.map[0] if token.map else 0
                heading_text = ""
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    heading_text = self._extract_plain_text(tokens[i + 1])
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, heading_text))
                heading_positions.append({
                    "line": line, "level": level,
                    "heading": heading_text,
                    "headings": [h for _, h in heading_stack],
                })
                i += 2
                continue
            i += 1

        if not heading_positions:
            content = text.strip()
            if content:
                sections.append(Section(
                    level=0, heading="", content=content,
                    headings=[], content_types=self._detect_content_types(content),
                    token_count=self._count_tokens(content),
                    line_start=0, line_end=len(lines),
                ))
            return sections

        pre_end = heading_positions[0]["line"]
        if pre_end > 0:
            pre_content = "\n".join(lines[0:pre_end]).strip()
            if pre_content:
                sections.append(Section(
                    level=0, heading="", content=self._clean_content(pre_content),
                    headings=[], content_types=self._detect_content_types(pre_content),
                    token_count=self._count_tokens(pre_content),
                    line_start=0, line_end=pre_end,
                ))

        for idx, pos in enumerate(heading_positions):
            content_start = pos["line"] + 1
            content_end = heading_positions[idx + 1]["line"] if idx + 1 < len(heading_positions) else len(lines)
            content = "\n".join(lines[content_start:content_end]).strip()
            content_types = self._detect_content_types(content)
            content = self._clean_content(content)
            sections.append(Section(
                level=pos["level"], heading=pos["heading"], content=content,
                headings=pos["headings"], content_types=content_types,
                token_count=self._count_tokens(content),
                line_start=pos["line"], line_end=content_end,
            ))

        return sections

    def _count_tokens(self, text: str) -> int:
        return len(self._TOKENIZER.encode(text))

    def split_markdown_into_chunks(
        self, sections: list[Section], chunk_size: int = 0, overlap: int = 0
    ) -> list[Chunk]:
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
                    level=last.level, heading=last.heading,
                    content=last.content + "\n\n" + sec.content,
                    headings=last.headings,
                    content_types=last.content_types | sec.content_types,
                    token_count=merged_token,
                    line_start=last.line_start, line_end=sec.line_end,
                    raw_code_blocks=last.raw_code_blocks + sec.raw_code_blocks,
                )
            else:
                merged.append(sec)
        return merged

    def _split_section(self, section: Section, chunk_size: int) -> list[Chunk]:
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
                source="", chunk_index=chunk_index,
                headings_path=section.headings,
                section_level=section.level,
                content_types=section.content_types,
                char_count=len(content), token_count=token_count,
                line_start=section.line_start, line_end=section.line_end,
                raw_code="\n\n".join(section.raw_code_blocks),
            ),
        )

    def _apply_overlap(self, chunks: list[Chunk], overlap: int) -> list[Chunk]:
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
                char_count=len(content), token_count=self._count_tokens(content),
                line_start=chunk.metadata.line_start, line_end=chunk.metadata.line_end,
                prev_chunk_index=i - 1 if i > 0 else None,
                next_chunk_index=i + 1 if i < len(chunks) - 1 else None,
                raw_code=chunk.metadata.raw_code,
            )
            result.append(Chunk(content=content, metadata=metadata))
        return result

    def _detect_content_types(self, content_text: str) -> ContentType:
        types = ContentType.TEXT
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

    def _extract_plain_text(self, inline_token) -> str:
        if not inline_token.children:
            return inline_token.content or ""
        return "".join(
            child.content for child in inline_token.children
            if child.type == "text" or child.type == "code_inline"
        ).strip()

    def _clean_content(self, text: str) -> str:
        protected = []

        def protect(match):
            protected.append(match.group())
            return f"__PROTECTED_{len(protected) - 1}__"

        text = re.sub(r'```[\s\S]*?```', protect, text)
        text = re.sub(r'\$\$[\s\S]*?\$\$', protect, text)
        text = re.sub(
            r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']+)["\'][^>]*\s*/?>',
            r'![\2](\1)', text
        )
        text = re.sub(
            r'<img\s+[^>]*alt=["\']([^"\']+)["\'][^>]*src=["\']([^"\']+)["\'][^>]*\s*/?>',
            r'![\1](\2)', text
        )
        text = re.sub(r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*\s*/?>', r'![图片](\1)', text)
        text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
        text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
        for tag in ['div', 'p', 'br', 'span', 'center', 'section']:
            text = re.sub(rf'<{tag}[^>]*>', '', text)
            text = re.sub(rf'</{tag}>', '', text)
        for i, block in enumerate(protected):
            text = text.replace(f"__PROTECTED_{i}__", block)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text

    async def enrich_sections(self, sections: list[Section]) -> list[Section]:
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
        new_token_count = self._count_tokens(content)
        return Section(
            level=section.level, heading=section.heading, content=content,
            headings=section.headings, content_types=section.content_types,
            token_count=new_token_count,
            line_start=section.line_start, line_end=section.line_end,
            raw_code_blocks=raw_code_blocks,
        )

    async def _replace_images(self, content: str) -> str:
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
        async with self._semaphore:
            try:
                prompt = f"请详细描述这张图片的内容，不超过80个字，不要分点，不要重复标题。图片的alt标签为：{alt}" if alt else "请详细描述这张图片的内容，不超过80个字"
                image_url = await self._resolve_image_url(url)
                response = await _client.chat.completions.create(
                    model=VISION_MODEL,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }],
                    max_tokens=512,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("视觉模型调用失败（url=%s）: %s", url, e)
                return f"[图片：{alt}]" if alt else "[图片]"

    async def _resolve_image_url(self, url: str) -> str:
        if url.startswith("data:"):
            return url
        if url.startswith(("http://", "https://")):
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
        async with self._semaphore:
            try:
                response = await _deepseek_client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[{
                        "role": "user",
                        "content": f"请用一句话简要总结以下代码的核心功能，不超过100个字：\n\n{code}",
                    }],
                    stream=False, temperature=0.3,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning("代码摘要模型调用失败: %s", e)
                return "[代码块]"

    def statistics(
        self,
        chunks: list[Chunk],
        min_tokens: int = 50,
        max_tokens: int = 0,
        histogram_step: int = 100,
    ) -> ChunkDistribution:
        if not chunks:
            return ChunkDistribution()

        max_tokens = max_tokens or int(self.chunk_size * 1.2)
        token_counts = [c.metadata.token_count for c in chunks]
        sorted_tokens = sorted(token_counts)
        n = len(sorted_tokens)

        def percentile(p: float) -> float:
            idx = (n - 1) * p
            lo, hi = int(idx), min(int(idx) + 1, n - 1)
            return sorted_tokens[lo] + (sorted_tokens[hi] - sorted_tokens[lo]) * (idx - lo)

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

        histogram: dict[str, int] = {}
        for t in token_counts:
            bucket_start = (t // histogram_step) * histogram_step
            bucket_end   = bucket_start + histogram_step
            key = f"{bucket_start}-{bucket_end}"
            histogram[key] = histogram.get(key, 0) + 1
        histogram = dict(sorted(histogram.items(), key=lambda x: int(x[0].split("-")[0])))

        empty_chunks     = [c.metadata.chunk_index for c in chunks if c.metadata.token_count == 0]
        too_small_chunks = [c.metadata.chunk_index for c in chunks if 0 < c.metadata.token_count < min_tokens]
        too_large_chunks = [c.metadata.chunk_index for c in chunks if c.metadata.token_count > max_tokens]
        orphan_chunks    = [c.metadata.chunk_index for c in chunks if not c.metadata.headings_path]

        return ChunkDistribution(
            total_chunks=n, total_tokens=sum(token_counts),
            total_chars=sum(c.metadata.char_count for c in chunks),
            token_min=sorted_tokens[0], token_max=sorted_tokens[-1],
            token_mean=stats_lib.mean(token_counts),
            token_median=stats_lib.median(token_counts),
            token_p25=percentile(0.25), token_p75=percentile(0.75),
            token_p95=percentile(0.95),
            token_stddev=stats_lib.stdev(token_counts) if n > 1 else 0.0,
            type_counts=type_counts, histogram=histogram,
            empty_chunks=empty_chunks, too_small_chunks=too_small_chunks,
            too_large_chunks=too_large_chunks, orphan_chunks=orphan_chunks,
        )
