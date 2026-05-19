from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchResult:
    content: str
    headings: list[str] = field(default_factory=list)
    source_file: str = ""
    score: float = 0.0
    content_types: int = 0
    token_count: int = 0
    char_count: int = 0
    raw_code: str = ""
    section_level: int = 0
    prev_chunk_index: Optional[int] = None
    next_chunk_index: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "headings": self.headings,
            "source_file": self.source_file,
            "score": self.score,
            "content_types": self.content_types,
            "token_count": self.token_count,
            "char_count": self.char_count,
            "raw_code": self.raw_code,
            "section_level": self.section_level,
            "prev_chunk_index": self.prev_chunk_index,
            "next_chunk_index": self.next_chunk_index,
        }
