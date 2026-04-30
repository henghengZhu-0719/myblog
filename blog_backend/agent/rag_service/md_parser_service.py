import re
import logging
import jieba
import json
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """按标题切分出的文档段落"""
    level: int
    heading: str
    content: str
    headings: list[str] = field(default_factory=list)


@dataclass
class Chunk:
    """切分后的文本片段，附带标题路径"""
    content: str
    headings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"content": self.content, "headings": self.headings}


class MarkdownParserService:
    """Markdown 文本切分服务，将长文档按标题层级和 chunk_size 切分为多个片段（chunk）"""

    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    # ------------------------------------------------------------------
    #  公共入口：执行完整的切分流程
    # ------------------------------------------------------------------

    def split_markdown_into_chunks(
        self, text: str, chunk_size: int, overlap: int
    ) -> list[Chunk]:
        """将 Markdown 文本切分为多个 chunk，每个 chunk 包含 content 和 headings（标题路径）"""
        # 将扁平标题（# 1.1）修复为正确层级（## 1.1）
        text = self._normalize_headings(text)
        # 按标题将文档拆分为多个 section
        sections = self._split_into_sections(text)
        # 合并长度较小的相邻 section，减少碎片
        sections = self._merge_small_sections(sections, chunk_size)
        # 对每个 section 进一步按 chunk_size 切分
        chunks: list[Chunk] = []
        for section in sections:
            chunks.extend(
                self._split_section(section, chunk_size)
            )
        # 在相邻 chunk 间叠加 overlap 字符，保持上下文连贯
        chunks = self._apply_overlap(chunks, overlap)
        return chunks

    # ------------------------------------------------------------------
    #  Step 1：修复扁平标题层级
    # ------------------------------------------------------------------

    def _normalize_headings(self, text: str) -> str:
        """将 MinerU 等工具生成的扁平标题（全部用 #）按编号层级还原：
           # 1.1 背景 → ## 1.1 背景；# 1.1.1 细节 → ### 1.1.1 细节"""
        def replace_heading(match):
            number = match.group(2)   # 编号文本，如 "1.1"
            title  = match.group(3).lstrip()
            depth  = number.count(".") + 1  # 根据小数点数量计算出标题层级
            return f"{'#' * depth} {number} {title}"

        return re.sub(
            r"^(#+) (\d+(?:\.\d+)+)(.*)",  # 匹配 "# 1.1" 或 "# 1.1.2" 格式
            replace_heading,
            text,
            flags=re.MULTILINE,
        )

    # ------------------------------------------------------------------
    #  Step 2：按标题切分为 Section 列表
    # ------------------------------------------------------------------

    def _split_into_sections(self, text: str) -> list[Section]:
        """按 Markdown 标题（#、##、###...）切分文本，返回包含 level / heading / content / headings 的列表"""
        # 将代码块内容替换为占位符，避免代码块内的 # 被误识别为标题
        code_blocks: dict[str, str] = {}
        def replace_code_block(match):
            key = f"\x00CODE_BLOCK_{len(code_blocks)}\x00"
            code_blocks[key] = match.group(0)
            return key
        clean_text = re.sub(
            r"```.*?```",
            replace_code_block,
            text,
            flags=re.DOTALL,
        )

        # 匹配 1~6 级 Markdown 标题
        heading_pattern = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)
        matches = list(heading_pattern.finditer(clean_text))
        sections: list[Section] = []
        heading_stack: list[tuple[int, str]] = []  # 标题路径栈，记录从根到当前节点的 (层级, 标题文字)

        for i, match in enumerate(matches):
            level = len(match.group(1))  # # 的数量即标题层级
            heading = re.sub(r"\*+", "", match.group(2)).strip()  # 去除加粗/斜体标记

            # 当前标题到下一个标题之间的内容即为该 section 的正文
            content_start = match.end()
            content_end = matches[i + 1].start() if i + 1 < len(matches) else len(clean_text)
            content = clean_text[content_start:content_end].strip()
            # 还原代码块占位符
            for key, value in code_blocks.items():
                content = content.replace(key, value)

            # 维护标题路径栈：弹出层级 >= 当前层级的标题，保持正确的嵌套关系
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading))

            sections.append(Section(
                level=level,
                heading=heading,
                content=content,
                headings=[h for _, h in heading_stack],
            ))

        # 提取文档开头（第一个标题之前）的内容，作为无标题 section
        if matches:
            pre_content = clean_text[: matches[0].start()].strip()
            # 取文档第一个标题作为 fallback heading
            first_heading = re.sub(r"\*+", "", matches[0].group(2)).strip()
        else:
            pre_content = text.strip()
            first_heading = ""

        if pre_content:
            sections.insert(0, Section(
                level=0,
                heading="",
                content=pre_content,
                headings=[first_heading] if first_heading else [],
            ))

        return sections

    # ------------------------------------------------------------------
    #  Step 2.5：合并过小的 Section
    # ------------------------------------------------------------------

    def _merge_small_sections(self, sections: list[Section], chunk_size: int) -> list[Section]:
        """将相邻的小 section 合并，减少碎片 chunk；合并后总长度不超过 chunk_size"""
        if not sections:
            return []

        merged: list[Section] = []
        current = Section(**vars(sections[0]))

        for next_section in sections[1:]:
            current_len = len(current.content)
            next_len = len(next_section.content)

            if current_len + next_len <= chunk_size:
                # 合并时保留被合并 section 的标题行作为分隔
                if next_section.level > 0:
                    separator = f"\n\n{'#' * next_section.level} {next_section.heading}\n\n"
                else:
                    separator = "\n\n"

                current.content = (
                    current.content + separator + next_section.content
                ).strip()
            else:
                merged.append(current)
                current = Section(**vars(next_section))

        merged.append(current)
        return merged


    # ------------------------------------------------------------------
    #  Step 3：对单个 Section 按 chunk_size 切分
    # ------------------------------------------------------------------

    def _split_section(
        self, section: Section, chunk_size: int
    ) -> list[Chunk]:
        """对单个 section 的 content 进行切分，优先保持代码块和表格完整"""
        content = section.content
        headings = section.headings

        if not content:
            return []

        # 内容本身不超过 chunk_size，直接作为一个 chunk
        if len(content) <= chunk_size:
            return [Chunk(content=content, headings=headings)]

        # 先将内容拆分为块（代码块、表格、普通段落），再逐块分配
        blocks = self._split_into_blocks(content)
        chunks: list[Chunk] = []
        current_parts: list[str] = []
        current_len = 0

        for block in blocks:
            block_len = len(block)

            if block_len > chunk_size:
                # 单个块超长，先 flush 当前累积，再对该块进行降级切分
                if current_parts:
                    chunks.append(Chunk(content="\n\n".join(current_parts).strip(), headings=headings))
                    current_parts = []
                    current_len = 0
                for sub in self._split_long_block(block, chunk_size):
                    chunks.append(Chunk(content=sub, headings=headings))

            elif current_len + block_len > chunk_size:
                # 加上当前块会超长，先 flush 当前累积，再开启新块
                if current_parts:
                    chunks.append(Chunk(content="\n\n".join(current_parts).strip(), headings=headings))
                current_parts = [block]
                current_len = block_len

            else:
                # 正常累积
                current_parts.append(block)
                current_len += block_len

        # 处理剩余的内容
        if current_parts:
            chunks.append(Chunk(
                content="\n\n".join(current_parts).strip(),
                headings=headings,
            ))

        return chunks

    # ------------------------------------------------------------------
    #  块级拆分：识别代码块、表格、普通段落
    # ------------------------------------------------------------------

    def _split_into_blocks(self, text: str) -> list[str]:
        """将文本拆分为块级元素：代码块整体保留、表格整体保留、普通段落按空行切分"""
        blocks = []
        lines = text.split("\n")
        i = 0
        buffer = []

        while i < len(lines):
            line = lines[i]

            # 代码块：从 ``` 到下一个 ``` 整体作为一个块
            if line.strip().startswith("```"):
                if buffer:
                    blocks.extend(self._split_paragraph_buffer(buffer))
                    buffer = []
                code_lines = [line]
                i += 1
                while i < len(lines):
                    code_lines.append(lines[i])
                    if lines[i].strip().startswith("```") and len(code_lines) > 1:
                        i += 1
                        break
                    i += 1
                blocks.append("\n".join(code_lines))
                continue

            # 表格：以 | 开头的连续行整体作为一个块
            if line.strip().startswith("|"):
                if buffer:
                    blocks.extend(self._split_paragraph_buffer(buffer))
                    buffer = []
                table_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                blocks.append("\n".join(table_lines))
                continue

            # 普通行：暂存到 buffer 中
            buffer.append(line)
            i += 1

        # 处理剩余未刷新的普通行
        if buffer:
            blocks.extend(self._split_paragraph_buffer(buffer))

        return [b for b in blocks if b.strip()]

    def _split_paragraph_buffer(self, lines: list[str]) -> list[str]:
        """将普通行列表按空行切分为段落列表"""
        return [p.strip() for p in "\n".join(lines).split("\n\n") if p.strip()]

    # ------------------------------------------------------------------
    #  超长块降级处理：段落 → 句子 → 词（jieba） → 字符
    # ------------------------------------------------------------------

    def _split_long_block(self, block: str, chunk_size: int) -> list[str]:
        """对超长段落按句子切分；句子仍超长则降级到 jieba 分词/字符切割"""
        chunks = []
        # 按中文/英文句末标点切分为句子
        sentences = re.split(r"(?<=[。！？；!?;.])\s*", block)
        sentences = [s for s in sentences if s.strip()]
        current_parts: list[str] = []
        current_len = 0

        for sentence in sentences:
            if len(sentence) > chunk_size:
                # 单句超长，先 flush 当前累积，再对句子进行降级切分
                if current_parts:
                    chunks.append("".join(current_parts).strip())
                    current_parts = []
                    current_len = 0
                chunks.extend(self._split_long_sentence(sentence, chunk_size))
            elif current_len + len(sentence) > chunk_size:
                # 累积会超长，先 flush，再开启新片段
                if current_parts:
                    chunks.append("".join(current_parts).strip())
                current_parts = [sentence]
                current_len = len(sentence)
            else:
                current_parts.append(sentence)
                current_len += len(sentence)

        if current_parts:
            chunks.append("".join(current_parts).strip())

        return chunks

    def _split_long_sentence(self, sentence: str, chunk_size: int) -> list[str]:
        """使用 jieba 分词切割超长句子；失败时降级为字符切割"""
        chunks: list[str] = []
        try:
            words = list(jieba.cut(sentence))
            current_parts: list[str] = []
            current_len = 0
            for word in words:
                if current_len + len(word) > chunk_size and current_parts:
                    chunks.append("".join(current_parts))
                    current_parts = []
                    current_len = 0
                current_parts.append(word)
                current_len += len(word)
            if current_parts:
                chunks.append("".join(current_parts))
        except Exception as e:
            logger.warning("jieba split error: %s, fallback to char split", e)
            chunks = self._split_by_characters(sentence, chunk_size)
        return chunks

    @staticmethod
    def _split_by_characters(sentence: str, chunk_size: int) -> list[str]:
        """最终兜底：按固定字符数切割"""
        return [sentence[i: i + chunk_size] for i in range(0, len(sentence), chunk_size)]

    # ------------------------------------------------------------------
    #  Overlap 处理：在相邻 chunk 间叠加上下文
    # ------------------------------------------------------------------

    def _apply_overlap(self, chunks: list[Chunk], overlap: int) -> list[Chunk]:
        """在每个 chunk 开头追加前一个 chunk 末尾的 overlap 字符（代码块 chunk 除外）"""
        if not overlap or len(chunks) <= 1:
            return chunks

        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            curr = chunks[i]

            # 代码块 chunk 不参与 overlap（避免破坏代码语法）
            prev_is_code = prev.content.strip().startswith("```")
            curr_is_code = curr.content.strip().startswith("```")

            if prev_is_code or curr_is_code:
                result.append(curr)
                continue

            overlap_text = self._find_overlap_start(prev.content, overlap)
            result.append(Chunk(
                content=overlap_text + "\n\n" + curr.content,
                headings=curr.headings,
            ))
        return result

    def _find_overlap_start(self, text: str, overlap: int) -> str:
        """从 text 末尾取约 overlap 个字符，并回溯到最近的标点/空白边界"""
        if len(text) <= overlap:
            return text

        original_pos = len(text) - overlap
        pos = original_pos

        # 向前回溯到最近的分隔字符，避免切碎单词或 Markdown 符号
        boundary_chars = set(" \t\n，。！？；：、""''「」【】()（）*_`#>-")
        while pos > 0 and text[pos] not in boundary_chars:
            pos -= 1

        # 如果没找到任何分隔符，则使用原始位置硬切
        if pos == 0 and text[0] not in boundary_chars:
            pos = original_pos

        return text[pos:].lstrip()
# ==================== 测试 ====================

CHUNK_SIZE = 500
OVERLAP = 100

service = MarkdownParserService(chunk_size=CHUNK_SIZE, overlap=OVERLAP)

with open("/Users/zhuyq/Desktop/DeepAgents.md", "r", encoding="utf-8") as f:
    text = f.read()



chunks = service.split_markdown_into_chunks(text, CHUNK_SIZE, OVERLAP)


print(f"共切分为 {len(chunks)} 个 chunk\n")
for i, chunk in enumerate(chunks):
    print(f"【Chunk {i+1}】长度={len(chunk.content)}")
    # print(chunk.content)
    print(f"headings: {chunk.headings}")
    print("-" * 60)

# 保存chunks
with open("chunks.json", "w") as f:
    json.dump([c.to_dict() for c in chunks], f, ensure_ascii=False, indent=4)