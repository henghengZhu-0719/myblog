"""
解析规则管理工具模块。

把 ParsingMemory 包装成 subagent 可调用的 @tool 集。
专门给解析 agent 使用，管理网页解析规则的存、取、查、追踪。
"""

from datetime import datetime
from uuid import uuid4
from typing import Optional

from langchain_core.tools import tool
from memory.base import MemoryItem
from memory.types.parsing import ParsingMemory


def create_parsing_tools(parsing_memory: ParsingMemory) -> list:
    """创建解析规则管理相关的工具列表。"""

    @tool
    def save_parse_rule(
        url: str,
        domain: str,
        rule_type: str,
        description: str,
        parse_rule: str,
        tags: Optional[str] = None,
    ) -> str:
        """保存一条网页解析规则。

        Args:
            url: 目标网页 URL
            domain: 所属域名（如 example.com）
            rule_type: 规则类型（如 css_selector / xpath / regex / json_path）
            description: 规则描述，说明这个规则用来解析什么内容
            parse_rule: 解析规则本体（CSS 选择器、XPath 表达式等）
            tags: 标签，多个用逗号分隔（如 "标题,正文,列表"）
        """
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        rule_id = str(uuid4())

        item = MemoryItem(
            id=rule_id,
            content=description,
            memory_type="parsing",
            user_id="default",
            timestamp=datetime.now(),
            importance=0.5,
            metadata={
                "url": url,
                "domain": domain,
                "rule_type": rule_type,
                "parse_rule": parse_rule,
                "tags": tag_list,
                "is_parsing_data": True,
            },
        )

        parsing_memory.add(item)
        return (
            f"解析规则已保存（ID: {rule_id}）\n"
            f"URL: {url}\n"
            f"域名: {domain}\n"
            f"类型: {rule_type}\n"
            f"描述: {description}"
        )

    @tool
    def search_parse_rules(
        query: str,
        domain: Optional[str] = None,
        rule_type: Optional[str] = None,
        limit: int = 5,
    ) -> str:
        """搜索已保存的解析规则。

        Args:
            query: 搜索关键词（匹配规则描述和 URL）
            domain: 按域名过滤（可选）
            rule_type: 按规则类型过滤（可选）
            limit: 最多返回几条结果
        """
        kwargs = {}
        if domain:
            kwargs["domain"] = domain
        if rule_type:
            kwargs["rule_type"] = rule_type

        items = parsing_memory.retrieve(query=query, limit=limit, **kwargs)
        if not items:
            return "没有找到匹配的解析规则。"

        lines = [f"--- 找到 {len(items)} 条解析规则 ---"]
        for i, item in enumerate(items, 1):
            meta = item.metadata or {}
            success = meta.get("success_count", 0)
            failure = meta.get("failure_count", 0)
            total = success + failure
            rate = f"{success / total * 100:.0f}%" if total > 0 else "暂无数据"

            lines.append(
                f"{i}. [{meta.get('rule_type', '?')}] {item.content[:100]}"
            )
            lines.append(f"   URL: {meta.get('url', '?')}")
            lines.append(f"   域名: {meta.get('domain', '?')}")
            lines.append(f"   成功率: {rate}")

        return "\n".join(lines)

    @tool
    def get_parse_rules_by_domain(domain: str) -> str:
        """获取指定域名的所有解析规则。

        Args:
            domain: 域名（如 example.com）
        """
        parses = parsing_memory.get_domain_parses(domain)
        if not parses:
            return f"域名 {domain} 下没有找到解析规则。"

        lines = [f"--- 域名 {domain} 的解析规则（共 {len(parses)} 条）---"]
        for i, p in enumerate(parses, 1):
            total = p.success_count + p.failure_count
            rate = f"{p.success_count / total * 100:.0f}%" if total > 0 else "暂无数据"
            lines.append(
                f"{i}. [{p.rule_type}] {p.description[:80]}"
            )
            lines.append(f"   URL: {p.url}")
            lines.append(f"   规则: {p.parse_rule[:100]}")
            lines.append(f"   成功率: {rate}（成功 {p.success_count} / 失败 {p.failure_count}）")

        return "\n".join(lines)

    @tool
    def record_parse_result(rule_id: str, success: bool) -> str:
        """记录一次解析规则的执行结果（成功或失败）。

        Args:
            rule_id: 解析规则的 ID
            success: True 表示解析成功，False 表示解析失败
        """
        if not parsing_memory.has_memory(rule_id):
            return f"未找到 ID 为 {rule_id} 的解析规则。"

        if success:
            parsing_memory.record_success(rule_id)
            return f"规则 {rule_id} 解析成功 ✓（已记录）"
        else:
            parsing_memory.record_failure(rule_id)
            return f"规则 {rule_id} 解析失败 ✗（已记录）"

    @tool
    def delete_parse_rule(rule_id: str) -> str:
        """删除一条解析规则。

        Args:
            rule_id: 要删除的解析规则 ID
        """
        if not parsing_memory.has_memory(rule_id):
            return f"未找到 ID 为 {rule_id} 的解析规则。"

        parsing_memory.remove(rule_id)
        return f"解析规则 {rule_id} 已删除。"

    return [
        save_parse_rule,
        search_parse_rules,
        get_parse_rules_by_domain,
        record_parse_result,
        delete_parse_rule,
    ]
