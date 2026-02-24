"""
Agent System 事件发射器
将 Agent 操作改造为事件驱动模式
"""
from pathlib import Path
import sys

# 添加路径
AIOS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AIOS_ROOT))

from core.event import create_event, EventType
from core.event_bus import emit


def emit_agent_created(agent_id: str, role: str, model: str):
    """发射 agent 创建事件"""
    event = create_event(
        EventType.AGENT_CREATED,
        source="agent_system",
        agent_id=agent_id,
        role=role,
        model=model
    )
    emit(event)


def emit_agent_task_started(agent_id: str, task: str, session_key: str):
    """发射 agent 任务开始事件"""
    event = create_event(
        EventType.AGENT_TASK_STARTED,
        source="agent_system",
        agent_id=agent_id,
        task=task,
        session_key=session_key
    )
    emit(event)


def emit_agent_task_completed(agent_id: str, task: str, duration_ms: int, success: bool):
    """发射 agent 任务完成事件"""
    event = create_event(
        EventType.AGENT_TASK_COMPLETED,
        source="agent_system",
        agent_id=agent_id,
        task=task,
        duration_ms=duration_ms,
        success=success
    )
    emit(event)


def emit_agent_error(agent_id: str, error: str, error_type: str = "unknown"):
    """发射 agent 错误事件"""
    event = create_event(
        EventType.AGENT_ERROR,
        source="agent_system",
        agent_id=agent_id,
        error=error,
        error_type=error_type
    )
    emit(event)
