"""
Notifier - 通知抽象层

提供可插拔的通知接口，默认 PrintNotifier 只打印到控制台。
用户可以实现自己的 Notifier 子类（如 TelegramNotifier）。
"""

from datetime import datetime
from typing import Dict, Optional


class Notifier:
    """通知基类（抽象接口）"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def notify_improvement(self, agent_id: str, improvements_applied: int, details: Dict = None):
        """改进应用通知"""
        pass

    def notify_rollback(self, agent_id: str, reason: str, metrics: Dict = None):
        """回滚告警"""
        pass

    def notify_daily_summary(self, stats: Dict):
        """每日统计报告"""
        pass


class PrintNotifier(Notifier):
    """控制台打印通知（默认实现）"""

    def notify_improvement(self, agent_id: str, improvements_applied: int, details: Dict = None):
        if not self.enabled:
            return
        msg = f"🔧 [{agent_id}] 应用了 {improvements_applied} 项自动改进"
        if details:
            for k, v in details.items():
                msg += f"\n  • {k}: {v}"
        print(msg)

    def notify_rollback(self, agent_id: str, reason: str, metrics: Dict = None):
        if not self.enabled:
            return
        msg = f"⚠️ [{agent_id}] 自动回滚: {reason}"
        if metrics:
            before = metrics.get("before_metrics", {})
            after = metrics.get("after_metrics", {})
            if "success_rate" in before:
                msg += f"\n  成功率: {before['success_rate']:.1%} → {after.get('success_rate', 0):.1%}"
            if "avg_duration_sec" in before:
                msg += f"\n  耗时: {before['avg_duration_sec']:.1f}s → {after.get('avg_duration_sec', 0):.1f}s"
        print(msg)

    def notify_daily_summary(self, stats: Dict):
        if not self.enabled:
            return
        print(f"📊 Self-Improving Loop 报告:")
        print(f"  总 Agent: {stats.get('total_agents', 0)}")
        print(f"  总改进: {stats.get('total_improvements', 0)}")
        print(f"  总回滚: {stats.get('total_rollbacks', 0)}")
