# research_subagent/adapters/github_adapter.py

from datetime import datetime, timezone
from typing import Any
import requests

from .base import BaseAdapter, AdapterResult


class GitHubAdapter(BaseAdapter):
    """
    GitHub Adapter:
    通过 GitHub Search API 搜索和 Agent 相关的开源项目。
    """

    def fetch(
        self,
        source: dict[str, Any],
        queries: list[str],
    ) -> list[AdapterResult]:
        results: list[AdapterResult] = []

        for query in queries:
            params = {
                "q": f"{query} in:name,description,readme",
                "sort": source.get("sort", "updated"),
                "order": source.get("order", "desc"),
                "per_page": source.get("per_page", 10),
            }

            response = requests.get(
                source["url"],
                params=params,
                timeout=self.timeout,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "agent-research-bot",
                },
            )
            response.raise_for_status()

            data = response.json()

            for item in data.get("items", []):
                title = item.get("full_name", "")
                description = item.get("description") or ""

                text = f"{title} {description}"

                if not self.match_query(text, queries):
                    continue

                results.append(
                    {
                        "title": title,
                        "url": item.get("html_url", ""),
                        "content": description,
                        "source_id": source["id"],
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "published_at": item.get("created_at", ""),
                        "raw": item,
                    }
                )

        return results