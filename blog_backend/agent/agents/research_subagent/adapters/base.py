import time
from abc import ABC, abstractmethod
import logging
from typing import Any, TypedDict


class AdapterResult(TypedDict):
    title: str
    url: str
    content: str
    source_id: str
    fetched_at: str
    published_at: str
    raw: dict[str, Any]


class BaseAdapter(ABC):
    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: float = 1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def fetch(
        self,
        source: dict[str, Any],
        queries: list[str],
    ) -> list[AdapterResult]:
        raise NotImplementedError

    def safe_fetch(
        self,
        source: dict[str, Any],
        queries: list[str],
    ) -> list[AdapterResult]:
        if not self.validate_source(source):
            self.logger.warning(f"Invalid source config: {source}")
            return []

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                results = self.fetch(source, queries)
                self.logger.info(
                    f"Fetched {len(results)} results from {source.get('id')}"
                )
                return results

            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Fetch attempt {attempt}/{self.max_retries} failed "
                    f"for source {source.get('id')}: {e}"
                )

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)

        self.logger.error(
            f"Fetch failed after {self.max_retries} attempts "
            f"for source {source.get('id')}: {last_error}",
            exc_info=True,
        )
        return []

    def match_query(self, text: str, queries: list[str]) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(q.lower() in text_lower for q in queries)

    def validate_source(self, source: dict[str, Any]) -> bool:
        required = {"id", "type", "url"}
        return required.issubset(source.keys())

    def safe_get(self, data: dict[str, Any], key: str, default: Any = "") -> Any:
        return data.get(key, default)