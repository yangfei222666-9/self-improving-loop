"""
Self-Improving Loop - Core Module

让 AI Agent 自动进化的完整闭环系统
"""

__version__ = "0.1.1"
__author__ = "Self-Improving Loop Contributors"

from .core import SelfImprovingLoop
from .adapters import ConfigAdapter
from .rollback import AutoRollback
from .threshold import AdaptiveThreshold
from .notifier import TelegramNotifier
from .trace_store import JsonlTraceStore, SQLiteTraceStore
from .yijing import YijingEvolutionStrategy

__all__ = [
    "SelfImprovingLoop",
    "ConfigAdapter",
    "AutoRollback",
    "AdaptiveThreshold",
    "TelegramNotifier",
    "JsonlTraceStore",
    "SQLiteTraceStore",
    "YijingEvolutionStrategy",
]
