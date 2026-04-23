import re
from typing import List, Optional


class ChunkService:

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50,  # 过小的块直接合并到上一块
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

        # 匹配标题行：# / ## / ### ...
        self.header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def _parse_sections(self, text: str) -> List[dict]:
        """
        将 Markdown 文本解析为带层级的 section 列表

        返回格式：
        [
            {
                "level": 1,
                "heading": "一级标题",
                "content": "标题下的正文内容",
                "breadcrumb": ["一级标题"]
            },
            ...
        ]
        """
        sections = []
        # 找到所有标题的位置
        matches = list(self.header_pattern.finditer(text))

        # 没有任何标题，整个文本作为一个块
        if not matches:
            return [{"level": 0, "heading": "", "content": text, "breadcrumb": []}]

        # 标题前的内容（前言部分）
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                sections.append({
                    "level": 0,
                    "heading": "",
                    "content": preamble,
                    "breadcrumb": []
                })

        # 遍历每个标题，提取其正文
        for i, match in enumerate(matches):
            level = len(match.group(1))       # # 的数量即层级
            heading = match.group(2).strip()

            # 正文范围：当前标题结束 → 下一个标题开始
            content_start = match.end()
            content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[content_start:content_end].strip()

            sections.append({
                "level": level,
                "heading": heading,
                "content": content,
                "breadcrumb": []   # 后面填充
            })

        # 填充面包屑（记录祖先标题路径）
        self._fill_breadcrumb(sections)

        return sections

    def _fill_breadcrumb(self, sections: List[dict]):
        """
        为每个 section 填充祖先标题路径
        例如：# A → ## B → ### C 的面包屑是 ["A", "B", "C"]
        """
        stack = []  # (level, heading)
        for sec in sections:
            level = sec["level"]
            if level == 0:
                continue
            # 弹出层级 >= 当前的祖先
            stack = [(l, h) for l, h in stack if l < level]
            stack.append((level, sec["heading"]))
            sec["breadcrumb"] = [h for _, h in stack]

    def _further_split(self, text: str) -> List[str]:
        """
        当单个 section 内容仍超过 chunk_size 时，
        退化为按段落 → 句子递归切分
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        # 先按段落切
        paragraphs = re.split(r"\n{2,}", text)
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 1 <= self.chunk_size:
                current = (current + "\n\n" + para).strip()
            else:
                if current:
                    chunks.append(current)
                # 单段落还是太长，按句子切
                if len(para) > self.chunk_size:
                    sentences = re.split(r"(?<=[。！？.!?])", para)
                    current = ""
                    for sent in sentences:
                        if len(current) + len(sent) <= self.chunk_size:
                            current += sent
                        else:
                            if current:
                                chunks.append(current)
                            current = sent
                    if current:
                        chunks.append(current)
                    current = ""
                else:
                    current = para

        if current:
            chunks.append(current)

        return chunks

    def split_text(self, text: str) -> List[dict]:
        """
        主入口：返回带元数据的 chunk 列表

        返回格式：
        [
            {
                "text": "chunk 正文",
                "heading": "所属标题",
                "level": 2,
                "breadcrumb": ["一级标题", "二级标题"],
                "breadcrumb_str": "一级标题 > 二级标题"
            },
            ...
        ]
        """
        sections = self._parse_sections(text)
        chunks = []

        for sec in sections:
            heading = sec["heading"]
            level = sec["level"]
            breadcrumb = sec["breadcrumb"]
            content = sec["content"]

            if not content:
                continue

            # 内容在 chunk_size 内，直接作为一个 chunk
            if len(content) <= self.chunk_size:
                sub_chunks = [content]
            else:
                # 超长，进一步切分
                sub_chunks = self._further_split(content)

            # 过滤太短的块，合并到上一块
            for text_chunk in sub_chunks:
                if len(text_chunk) < self.min_chunk_size and chunks:
                    chunks[-1]["text"] += "\n\n" + text_chunk
                else:
                    chunks.append({
                        "text": text_chunk,
                        "heading": heading,
                        "level": level,
                        "breadcrumb": breadcrumb,
                        "breadcrumb_str": " > ".join(breadcrumb)
                    })

        return chunks
