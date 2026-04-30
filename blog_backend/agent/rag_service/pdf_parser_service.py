import json
import re 
import jieba
logger = logging.getLogger(__name__)

class PdfParserService():

    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_text_into_chunks_with_semantics(self, text: str, chunk_size: int, overlap: int) -> list:
        """
        基于语义分割文本，优先按照段落保持语义完整，即最小为每段一个chunk
        - 段落 ≤ chunk_size：尽量合并到同一块
        - 段落 > chunk_size：调用 _split_long_paragraph 进一步拆分
        """
        chunks: list[str] = []
        paragraphs = re.split(r"\n\n+", text) # 两个换行为一个段落
        current_chunk = []
        current_len = 0
        for paragraph in paragraphs:
            # 当前段落长度大于chunk_size
            if len(paragraph) > chunk_size:
                # 该 paragraph 无法加入到current_chunk，故先保存current_chunk，再处理该paragraph
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk).strip())
                    # 重制 current-chunk
                    current_chunk = [] 
                    current_len = 0
                # 对于长段落进行句子级别拆分
                chunks.extend(self._split_long_paragraph(paragraph, chunk_size))
            
            elif current_len + len(paragraph) > chunk_size:
                # current-chunk 无法加入该 paragraph
                if current_chunk:
                    # 引入 overlap
                    chunk_text = "\n\n".join(current_chunk).strip()
                    
                    chunks.append(chunk_text)
                    # 去上一个chunks 的末尾作为 overlap 前缀
                    overlap_text = chunk_text[-overlap:] if overlap else ""
                    current_chunk = ([overlap_text] if overlap_text else []) + [paragraph]
                    current_len =  len(overlap_text) + len(paragraph)
                else:
                    current_chunk.append(paragraph)
                    current_len += len(paragraph)

            else:
                current_chunk.append(paragraph)
                current_len += len(paragraph)
        # 将最后一个current-chunk 保存        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk).strip())

        return chunks
    
    def _split_long_paragraph(self, paragraph: str, chunk_size: int) -> list:
        """
        按句子边界（。！？；. ! ? ;）拆分长段落。
        若单句仍超限，则调用 _split_long_sentence。
        """
        chunks: list[str] = []
        sentences = re.split(r"(?<=[。！？；])|(?<=[.!?;])\s+", paragraph)
        current_chunk = []
        current_len = 0

        for sentence in sentences:
            if len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append("".join(current_chunk).strip())
                    current_chunk = []
                    current_len = 0
                # 对长句子进行拆分
                chunks.extend(self._split_long_sentence(sentence, chunk_size))

            elif current_len + len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append("".join(current_chunk).strip())
                    current_chunk = []
                    current_len = 0
                current_chunk.append(sentence)
                current_len = len(sentence)
            else:
                current_chunk.append(sentence)
                current_len += len(sentence)
        if current_chunk:
            chunks.append("".join(current_chunk).strip())
        return chunks

    def _split_long_sentence(self, sentence: str, chunk_size: int) -> list[str]:
        """
        使用 jieba 分词对超长句子进行语义切割，失败则降级为按字符切割
        """
        chunks: list[str] = []
        try:
            words = list(jieba.cut(sentence))
            current_chunk: list[str] = []
            current_len = 0

            for word in words:
                if current_len + len(word) > chunk_size and current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                current_chunk.append(word)
                current_len += len(word)

            if current_chunk:
                chunks.append("".join(current_chunk))

        except Exception as e:
            logger.warning("jieba 分词异常: %s，使用字符分割作为备用方案", e)
            chunks = self._split_by_characters(sentence, chunk_size)

        return chunks
    @staticmethod
    def _split_by_characters(self, sentence: str, chunk_size: int) -> list[str]:
        """
        备用方案：按字符逐个切割，确保每块不超过 chunk_size。
        """
        chunks: list[str] = []
        for i in range(0, len(sentence), chunk_size):
            chunks.append(sentence[i : i + chunk_size])
        return chunks





# ==================== 测试 ====================

CHUNK_SIZE = 500
OVERLAP = 50

service = PdfParserService(chunk_size=CHUNK_SIZE, overlap=OVERLAP)

with open("/Users/zhuyq/Documents/trae_projects/MinerU/output/29653d85-801e-4084-a8a2-8ec16dbbe748/2/hybrid_auto/2.md", "r", encoding="utf-8") as f:
    text = f.read()



chunks = service.split_text_into_chunks_with_semantics(text, CHUNK_SIZE, OVERLAP)


print(f"共切分为 {len(chunks)} 个 chunk\n")
for i, chunk in enumerate(chunks):
    print(f"【Chunk {i+1}】长度={len(chunk)}")
    print(chunk)
    print("-" * 60)

# 保存chunks
with open("chunks.json", "w") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=4)