"""Refind Job Agent.

This module provides a job search agent using the deepagents package
with custom tools for web search and strategic thinking.
"""

from .prompts import (
    JOB_SEARCHER_INSTRUCTIONS,
    REFINDJOB_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
)
from .tools import job_tavily_search, job_think_tool

__all__ = [
    "job_tavily_search",
    "job_think_tool",
    "JOB_SEARCHER_INSTRUCTIONS",
    "REFINDJOB_WORKFLOW_INSTRUCTIONS",
    "SUBAGENT_DELEGATION_INSTRUCTIONS",
]
