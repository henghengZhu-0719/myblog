from dataclasses import dataclass, field
from enum import Flag, auto
from typing import Optional


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
    source: str
    chunk_index: int
    headings_path: list[str] = field(default_factory=list)
    section_level: int = 0
    content_types: ContentType = ContentType.TEXT
    line_start: int = 0
    line_end: int = 0
    char_count: int = 0
    token_count: int = 0
    prev_chunk_index: Optional[int] = None
    next_chunk_index: Optional[int] = None
    raw_code: str = ""

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


@dataclass
class ChunkDistribution:
    total_chunks:   int = 0
    total_tokens:   int = 0
    total_chars:    int = 0
    token_min:      int = 0
    token_max:      int = 0
    token_mean:     float = 0.0
    token_median:   float = 0.0
    token_p25:      float = 0.0
    token_p75:      float = 0.0
    token_p95:      float = 0.0
    token_stddev:   float = 0.0
    type_counts: dict[str, int] = field(default_factory=dict)
    empty_chunks:      list[int] = field(default_factory=list)
    too_small_chunks:  list[int] = field(default_factory=list)
    too_large_chunks:  list[int] = field(default_factory=list)
    orphan_chunks:     list[int] = field(default_factory=list)
    histogram: dict[str, int] = field(default_factory=dict)

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
