"""
AIOS Evolution Events - 进化事件集成

将进化系统集成到 AIOS EventBus，发送事件到 Dashboard
"""

import json
import time
from pathlib import Path


class EvolutionEventEmitter:
    """进化事件发射器"""

    def __init__(self):
        self.events_file = Path.home() / ".openclaw" / "workspace" / "aios" / "data" / "events.jsonl"
        self.events_file.parent.mkdir(parents=True, exist_ok=True)

    def emit_event(self, event_type: str, agent_id: str, payload: dict):
        """
        发送进化事件

        Args:
            event_type: 事件类型
            agent_id: Agent ID
            payload: 事件数据
        """
        event = {
            "id": f"evolution-{int(time.time() * 1000)}",
            "type": event_type,
            "source": f"evolution.{agent_id}",
            "timestamp": int(time.time()),
            "payload": payload
        }

        # 追加到事件日志
        with open(self.events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def emit_candidate(self, agent_id: str, strategies: list, risk: str):
        """发送候选进化事件（策略匹配但未应用）"""
        self.emit_event(
            event_type="evolution.candidate",
            agent_id=agent_id,
            payload={
                "agent_id": agent_id,
                "strategies": strategies,
                "risk": risk,
                "auto_apply": risk == "low"
            }
        )

    def emit_applied(self, agent_id: str, plans: list):
        """发送进化应用事件"""
        self.emit_event(
            event_type="evolution.applied",
            agent_id=agent_id,
            payload={
                "agent_id": agent_id,
                "plans": plans,
                "count": len(plans)
            }
        )

    def emit_evaluation(self, agent_id: str, before_score: float, after_score: float, action: str):
        """发送进化评估事件"""
        self.emit_event(
            event_type="evolution.evaluation",
            agent_id=agent_id,
            payload={
                "agent_id": agent_id,
                "before_score": before_score,
                "after_score": after_score,
                "delta": after_score - before_score,
                "action": action  # keep / rollback / observe
            }
        )

    def emit_rolled_back(self, agent_id: str, reason: str):
        """发送回滚事件"""
        self.emit_event(
            event_type="evolution.rolled_back",
            agent_id=agent_id,
            payload={
                "agent_id": agent_id,
                "reason": reason
            }
        )

    def emit_blocked(self, agent_id: str, reason: str):
        """发送阻止事件（熔断/冷却期）"""
        self.emit_event(
            event_type="evolution.blocked",
            agent_id=agent_id,
            payload={
                "agent_id": agent_id,
                "reason": reason
            }
        )


# 全局实例
_emitter = None


def get_emitter():
    """获取全局事件发射器"""
    global _emitter
    if _emitter is None:
        _emitter = EvolutionEventEmitter()
    return _emitter
