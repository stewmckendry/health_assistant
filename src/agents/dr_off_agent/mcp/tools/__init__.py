"""
MCP tools for Dr. OFF Ontario healthcare queries.
All tools implement dual-path retrieval (SQL + vector in parallel).
"""

from .schedule import schedule_get, ScheduleTool
from .adp import adp_get, ADPTool
from .odb import odb_get, ODBTool
from .source import source_passages, SourceTool

# Import coverage from Session 2A if it exists
try:
    from .coverage import coverage_answer, CoverageAnswerTool
except ImportError:
    coverage_answer = None
    CoverageAnswerTool = None

__all__ = [
    "schedule_get",
    "ScheduleTool",
    "adp_get", 
    "ADPTool",
    "odb_get",
    "ODBTool",
    "source_passages",
    "SourceTool",
    "coverage_answer",
    "CoverageAnswerTool"
]