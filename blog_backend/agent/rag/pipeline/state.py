from typing import TypedDict, Annotated

from langgraph.graph import add_messages


class RagState(TypedDict):
    original_query:   str
    intent:           str
    dense_query:      str
    sparse_query:     str
    retrieved_chunks: list[dict]
    context:          str
    prompt:           str
    answer:           str
    messages:         Annotated[list, add_messages]
