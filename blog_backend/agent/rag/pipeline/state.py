from typing import TypedDict, Annotated
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator

class RagState(TypedDict):
    original_query:   str
    intent:           str
    dense_query:      str
    sparse_query:     str
    retrieved_chunks: list[dict]
    context:          str
    prompt:           str
    answer:           str
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
