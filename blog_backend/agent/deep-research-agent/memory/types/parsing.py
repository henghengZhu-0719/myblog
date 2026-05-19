"""解析记忆实现

按照第8章架构设计的解析记忆，提供：
- 网页解析规则的存储与管理
- URL/域名维度的规则组织
- 解析规则的语义检索
- 规则成功率追踪与优化
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import os
import json
import logging

logger = logging.getLogger(__name__)

from ..base import BaseMemory, MemoryItem, MemoryConfig
from ..storage import SQLiteDocumentStore
from ..embedding import get_text_embedder, get_dimension

class Parse:
    """解析记忆中的单条解析规则"""
    
    def __init__(
        self,
        parse_id: str,
        user_id: str,
        url: str,
        domain: str,
        rule_type: str,
        description: str,
        parse_rule: str,
        tags: Optional[List[str]] = None,
        success_count: int = 0,
        failure_count: int = 0,
        timestamp: datetime = None,
        is_parsing_data: bool = True
    ):
        self.parse_id = parse_id
        self.user_id = user_id
        self.url = url
        self.domain = domain
        self.rule_type = rule_type
        self.description = description
        self.parse_rule = parse_rule
        self.tags = tags or []
        self.success_count = success_count
        self.failure_count = failure_count
        self.timestamp = timestamp or datetime.now()
        self.is_parsing_data = is_parsing_data


class ParsingMemory(BaseMemory):
    """解析记忆实现
    
    特点：
    - 存储网页解析规则
    - 支持按URL/域名检索
    - 支持解析规则的语义搜索
    - 追踪规则成功率
    """

    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)

        # 本地缓存（内存）
        self.parses: List[Parse] = []
        self.sessions: Dict[str, List[str]] = {}

        # 权威文档存储（SQLite）
        db_dir = self.config.storage_path if hasattr(self.config, 'storage_path') else "./memory_data"
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "memory.db")
        self.doc_store = SQLiteDocumentStore(db_path=db_path)

        # 统一嵌入模型（多语言，默认1024维）
        self.embedder = get_text_embedder()

        # 向量存储（Qdrant - 使用连接管理器避免重复连接）
        from ..storage.qdrant_store import QdrantConnectionManager
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.vector_store = QdrantConnectionManager.get_instance(
            url=qdrant_url,
            api_key=qdrant_api_key,
            collection_name=os.getenv("QDRANT_COLLECTION", "ParsingVectors"),
            vector_size=get_dimension(getattr(self.embedder, 'dimension', 1024)),
            distance=os.getenv("QDRANT_DISTANCE", "cosine")
        )

    def add(self, memory_item: MemoryItem) -> str:
        """添加解析记忆项"""
        url = memory_item.metadata.get("url", "")
        domain = memory_item.metadata.get("domain", "")
        rule_type = memory_item.metadata.get("rule_type", "custom")
        description = memory_item.metadata.get("description", "")
        parse_rule = memory_item.metadata.get("parse_rule", "{}")
        tags = memory_item.metadata.get("tags", [])
        session_id = memory_item.metadata.get("session_id", "default_session")

        # 如果 parse_rule 是 dict 则转为 JSON 字符串
        if isinstance(parse_rule, dict):
            parse_rule = json.dumps(parse_rule, ensure_ascii=False)

        # 创建解析规则对象（内存缓存）
        parse_obj = Parse(
            parse_id=memory_item.id,
            user_id=memory_item.user_id,
            url=url,
            domain=domain,
            rule_type=rule_type,
            description=description,
            parse_rule=parse_rule,
            tags=tags,
            success_count=memory_item.metadata.get("success_count", 0),
            failure_count=memory_item.metadata.get("failure_count", 0),
            timestamp=memory_item.timestamp,
            is_parsing_data=memory_item.metadata.get("is_parsing_data", True)
        )
        self.parses.append(parse_obj)
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(parse_obj.parse_id)

        # 1) 权威存储（SQLite）
        ts_int = int(memory_item.timestamp.timestamp())
        self.doc_store.add_memory(
            memory_id=memory_item.id,
            user_id=memory_item.user_id,
            content=description,
            memory_type="parsing",
            timestamp=ts_int,
            importance=memory_item.importance,
            properties={
                "url": url,
                "domain": domain,
                "rule_type": rule_type,
                "parse_rule": parse_rule,
                "tags": tags,
                "success_count": parse_obj.success_count,
                "failure_count": parse_obj.failure_count,
                "session_id": session_id,
                "is_parsing_data": parse_obj.is_parsing_data
            }
        )

        # 2) 向量索引（Qdrant）- 使用 description 作为嵌入文本
        try:
            embedding = self.embedder.encode(description)
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            self.vector_store.add_vectors(
                vectors=[embedding],
                metadata=[{
                    "memory_id": memory_item.id,
                    "user_id": memory_item.user_id,
                    "memory_type": "parsing",
                    "importance": memory_item.importance,
                    "url": url,
                    "domain": domain,
                    "rule_type": rule_type,
                    "tags": tags,
                    "content": description
                }],
                ids=[memory_item.id]
            )
        except Exception:
            pass

        return memory_item.id

    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索解析记忆（结构化过滤 + 语义向量检索）"""
        user_id = kwargs.get("user_id")
        url = kwargs.get("url")
        domain = kwargs.get("domain")
        rule_type = kwargs.get("rule_type")
        time_range: Optional[Tuple[datetime, datetime]] = kwargs.get("time_range")
        importance_threshold: Optional[float] = kwargs.get("importance_threshold")

        # 结构化过滤候选（来自权威库）
        candidate_ids: Optional[set] = None
        if time_range is not None or importance_threshold is not None or url or domain:
            start_ts = int(time_range[0].timestamp()) if time_range else None
            end_ts = int(time_range[1].timestamp()) if time_range else None
            docs = self.doc_store.search_memories(
                user_id=user_id,
                memory_type="parsing",
                start_time=start_ts,
                end_time=end_ts,
                importance_threshold=importance_threshold,
                limit=1000
            )
            candidate_ids = set()
            for d in docs:
                props = d.get("properties", {}) or {}
                if url and props.get("url") != url:
                    continue
                if domain and props.get("domain") != domain:
                    continue
                if rule_type and props.get("rule_type") != rule_type:
                    continue
                candidate_ids.add(d["memory_id"])

        # 向量检索（Qdrant）
        try:
            query_vec = self.embedder.encode(query)
            if hasattr(query_vec, "tolist"):
                query_vec = query_vec.tolist()
            where = {"memory_type": "parsing"}
            if user_id:
                where["user_id"] = user_id
            if url:
                where["url"] = url
            if domain:
                where["domain"] = domain
            if rule_type:
                where["rule_type"] = rule_type
            hits = self.vector_store.search_similar(
                query_vector=query_vec,
                limit=max(limit * 5, 20),
                where=where
            )
        except Exception:
            hits = []

        # 过滤与重排
        now_ts = int(datetime.now().timestamp())
        results: List[Tuple[float, MemoryItem]] = []
        seen = set()
        for hit in hits:
            meta = hit.get("metadata", {})
            mem_id = meta.get("memory_id")
            if not mem_id or mem_id in seen:
                continue

            if candidate_ids is not None and mem_id not in candidate_ids:
                continue

            # 从权威库读取完整记录
            doc = self.doc_store.get_memory(mem_id)
            if not doc:
                continue

            vec_score = float(hit.get("score", 0.0))
            age_days = max(0.0, (now_ts - int(doc["timestamp"])) / 86400.0)
            recency_score = 1.0 / (1.0 + age_days)
            imp = float(doc.get("importance", 0.5))

            base_relevance = vec_score * 0.8 + recency_score * 0.2
            importance_weight = 0.8 + (imp * 0.4)
            combined = base_relevance * importance_weight

            props = doc.get("properties", {}) or {}
            item = MemoryItem(
                id=doc["memory_id"],
                content=doc["content"],
                memory_type=doc["memory_type"],
                user_id=doc["user_id"],
                timestamp=datetime.fromtimestamp(doc["timestamp"]),
                importance=doc.get("importance", 0.5),
                metadata={
                    **props,
                    "relevance_score": combined,
                    "vector_score": vec_score,
                    "recency_score": recency_score
                }
            )
            results.append((combined, item))
            seen.add(mem_id)

        # 若向量检索无结果，回退到简单关键词匹配（内存缓存）
        if not results:
            query_lower = query.lower()
            for p in self._filter_parses(user_id, url, domain, rule_type):
                if query_lower in p.description.lower() or query_lower in p.url.lower():
                    recency_score = 1.0 / (1.0 + max(0.0, (now_ts - int(p.timestamp.timestamp())) / 86400.0))
                    keyword_score = 0.5
                    base_relevance = keyword_score * 0.8 + recency_score * 0.2
                    importance_weight = 0.8 + (getattr(p, 'importance', 0.5) * 0.4)
                    combined = base_relevance * importance_weight

                    item = MemoryItem(
                        id=p.parse_id,
                        content=p.description,
                        memory_type="parsing",
                        user_id=p.user_id,
                        timestamp=p.timestamp,
                        importance=getattr(p, 'importance', 0.5),
                        metadata={
                            "url": p.url,
                            "domain": p.domain,
                            "rule_type": p.rule_type,
                            "parse_rule": p.parse_rule,
                            "tags": p.tags,
                            "success_count": p.success_count,
                            "failure_count": p.failure_count,
                            "is_parsing_data": p.is_parsing_data,
                            "relevance_score": combined
                        }
                    )
                    results.append((combined, item))

        results.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in results[:limit]]

    def update(
        self,
        memory_id: str,
        content: str = None,
        importance: float = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """更新解析记忆（SQLite为权威，Qdrant按需重嵌入）"""
        updated = False
        for parse_obj in self.parses:
            if parse_obj.parse_id == memory_id:
                if content is not None:
                    parse_obj.description = content
                if importance is not None:
                    pass
                if metadata is not None:
                    if "url" in metadata:
                        parse_obj.url = metadata["url"]
                    if "domain" in metadata:
                        parse_obj.domain = metadata["domain"]
                    if "rule_type" in metadata:
                        parse_obj.rule_type = metadata["rule_type"]
                    if "parse_rule" in metadata:
                        parse_obj.parse_rule = metadata["parse_rule"] if isinstance(metadata["parse_rule"], str) else json.dumps(metadata["parse_rule"], ensure_ascii=False)
                    if "tags" in metadata:
                        parse_obj.tags = metadata["tags"]
                    if "success_count" in metadata:
                        parse_obj.success_count = metadata["success_count"]
                    if "failure_count" in metadata:
                        parse_obj.failure_count = metadata["failure_count"]
                updated = True
                break

        # 更新SQLite
        doc_updated = self.doc_store.update_memory(
            memory_id=memory_id,
            content=content,
            importance=importance,
            properties=metadata
        )

        # 如内容（description）变更，重嵌入并upsert到Qdrant
        if content is not None:
            try:
                embedding = self.embedder.encode(content)
                if hasattr(embedding, "tolist"):
                    embedding = embedding.tolist()
                doc = self.doc_store.get_memory(memory_id)
                props = (doc.get("properties", {}) or {}) if doc else (metadata or {})
                payload = {
                    "memory_id": memory_id,
                    "user_id": doc["user_id"] if doc else "",
                    "memory_type": "parsing",
                    "importance": (doc.get("importance") if doc else importance) or 0.5,
                    "url": props.get("url", ""),
                    "domain": props.get("domain", ""),
                    "rule_type": props.get("rule_type", ""),
                    "tags": props.get("tags", []),
                    "content": content
                }
                self.vector_store.add_vectors(
                    vectors=[embedding],
                    metadata=[payload],
                    ids=[memory_id]
                )
            except Exception:
                pass

        return updated or doc_updated

    def remove(self, memory_id: str) -> bool:
        """删除解析记忆（SQLite + Qdrant）"""
        removed = False
        for i, parse_obj in enumerate(self.parses):
            if parse_obj.parse_id == memory_id:
                self.parses.pop(i)
                for session_id, parse_ids in self.sessions.items():
                    if memory_id in parse_ids:
                        parse_ids.remove(memory_id)
                        if not parse_ids:
                            del self.sessions[session_id]
                        break
                removed = True
                break

        doc_deleted = self.doc_store.delete_memory(memory_id)

        try:
            self.vector_store.delete_memories([memory_id])
        except Exception:
            pass

        return removed or doc_deleted

    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        return any(parse_obj.parse_id == memory_id for parse_obj in self.parses)

    def clear(self):
        """清空所有解析记忆"""
        self.parses.clear()
        self.sessions.clear()

        docs = self.doc_store.search_memories(memory_type="parsing", limit=10000)
        ids = [d["memory_id"] for d in docs]
        for mid in ids:
            self.doc_store.delete_memory(mid)

        try:
            if ids:
                self.vector_store.delete_memories(ids)
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        """获取解析记忆统计信息"""
        db_stats = self.doc_store.get_database_stats()
        try:
            vs_stats = self.vector_store.get_collection_stats()
        except Exception:
            vs_stats = {"store_type": "qdrant"}

        total_success = sum(p.success_count for p in self.parses)
        total_failure = sum(p.failure_count for p in self.parses)
        domains = set(p.domain for p in self.parses)
        rule_types = {}
        for p in self.parses:
            rule_types[p.rule_type] = rule_types.get(p.rule_type, 0) + 1

        return {
            "count": len(self.parses),
            "total_count": len(self.parses),
            "sessions_count": len(self.sessions),
            "domains_count": len(domains),
            "domains": list(domains),
            "rule_types": rule_types,
            "total_success_count": total_success,
            "total_failure_count": total_failure,
            "success_rate": total_success / (total_success + total_failure) if (total_success + total_failure) > 0 else 0.0,
            "memory_type": "parsing",
            "vector_store": vs_stats,
            "document_store": {k: v for k, v in db_stats.items() if k.endswith("_count") or k in ["store_type", "db_path"]}
        }

    def get_all(self) -> List[MemoryItem]:
        """获取所有解析记忆（转换为MemoryItem格式）"""
        memory_items = []
        for parse_obj in self.parses:
            memory_item = MemoryItem(
                id=parse_obj.parse_id,
                content=parse_obj.description,
                memory_type="parsing",
                user_id=parse_obj.user_id,
                timestamp=parse_obj.timestamp,
                importance=0.5,
                metadata={
                    "url": parse_obj.url,
                    "domain": parse_obj.domain,
                    "rule_type": parse_obj.rule_type,
                    "parse_rule": parse_obj.parse_rule,
                    "tags": parse_obj.tags,
                    "success_count": parse_obj.success_count,
                    "failure_count": parse_obj.failure_count,
                    "is_parsing_data": parse_obj.is_parsing_data
                }
            )
            memory_items.append(memory_item)
        return memory_items

    def get_url_parses(self, url: str) -> List[Parse]:
        """获取指定URL的所有解析规则"""
        return [p for p in self.parses if p.url == url]

    def get_domain_parses(self, domain: str) -> List[Parse]:
        """获取指定域名的所有解析规则"""
        return [p for p in self.parses if p.domain == domain]

    def get_rule_type_parses(self, rule_type: str) -> List[Parse]:
        """获取指定规则类型的所有解析规则"""
        return [p for p in self.parses if p.rule_type == rule_type]

    def get_top_rules(self, limit: int = 10) -> List[Parse]:
        """获取成功率最高的解析规则"""
        sorted_parses = sorted(
            self.parses,
            key=lambda p: p.success_count / (p.success_count + p.failure_count + 1) if (p.success_count + p.failure_count) > 0 else 0,
            reverse=True
        )
        return sorted_parses[:limit]

    def record_success(self, memory_id: str) -> bool:
        """记录一次解析成功"""
        for parse_obj in self.parses:
            if parse_obj.parse_id == memory_id:
                parse_obj.success_count += 1
                self.doc_store.update_memory(
                    memory_id=memory_id,
                    properties={"success_count": parse_obj.success_count}
                )
                return True
        return False

    def record_failure(self, memory_id: str) -> bool:
        """记录一次解析失败"""
        for parse_obj in self.parses:
            if parse_obj.parse_id == memory_id:
                parse_obj.failure_count += 1
                self.doc_store.update_memory(
                    memory_id=memory_id,
                    properties={"failure_count": parse_obj.failure_count}
                )
                return True
        return False

    def get_stats_by_domain(self, domain: str = None) -> Dict[str, Any]:
        """获取指定域名的解析统计"""
        parses = [p for p in self.parses if p.domain == domain] if domain else self.parses
        if not parses:
            return {}

        total_success = sum(p.success_count for p in parses)
        total_failure = sum(p.failure_count for p in parses)
        rule_types = {}
        for p in parses:
            rule_types[p.rule_type] = rule_types.get(p.rule_type, 0) + 1

        return {
            "domain": domain or "all",
            "count": len(parses),
            "rule_types": rule_types,
            "total_success_count": total_success,
            "total_failure_count": total_failure,
            "success_rate": total_success / (total_success + total_failure) if (total_success + total_failure) > 0 else 0.0
        }

    def _filter_parses(
        self,
        user_id: str = None,
        url: str = None,
        domain: str = None,
        rule_type: str = None
    ) -> List[Parse]:
        """过滤解析规则"""
        filtered = self.parses

        if user_id:
            filtered = [p for p in filtered if p.user_id == user_id]
        if url:
            filtered = [p for p in filtered if p.url == url]
        if domain:
            filtered = [p for p in filtered if p.domain == domain]
        if rule_type:
            filtered = [p for p in filtered if p.rule_type == rule_type]

        return filtered
