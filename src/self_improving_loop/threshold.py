"""
Adaptive Threshold - 自适应阈值

根据 Agent 特性动态调整失败阈值。

阈值策略：
- 高频任务 Agent（>10 次/天）：阈值 5 次，窗口 48h，冷却 3h
- 中频任务 Agent（3-10 次/天）：阈值 3 次，窗口 24h，冷却 6h
- 低频任务 Agent（<3 次/天）：阈值 2 次，窗口 72h，冷却 12h
- 关键任务 Agent：阈值 1 次，窗口 24h，冷却 6h
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional


class AdaptiveThreshold:
    """自适应阈值管理器"""

    DEFAULT_FAILURE_THRESHOLD = 3
    DEFAULT_ANALYSIS_WINDOW_HOURS = 24
    DEFAULT_COOLDOWN_HOURS = 6

    HIGH_FREQUENCY_THRESHOLD = 10
    LOW_FREQUENCY_THRESHOLD = 3

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path.cwd() / "data" / "adaptive_thresholds.json"
        self.config = self._load_config()

    def get_threshold(self, agent_id: str, task_history: list) -> Tuple[int, int, int]:
        """
        获取 Agent 的自适应阈值

        Returns:
            (失败阈值, 分析窗口小时数, 冷却期小时数)
        """
        if agent_id in self.config:
            c = self.config[agent_id]
            return (
                c.get("failure_threshold", self.DEFAULT_FAILURE_THRESHOLD),
                c.get("analysis_window_hours", self.DEFAULT_ANALYSIS_WINDOW_HOURS),
                c.get("cooldown_hours", self.DEFAULT_COOLDOWN_HOURS),
            )

        frequency = self._calculate_frequency(task_history)
        is_critical = self._is_critical_agent(agent_id)

        if is_critical:
            return (1, 24, 6)
        elif frequency == "high":
            return (5, 48, 3)
        elif frequency == "low":
            return (2, 72, 12)
        else:
            return (self.DEFAULT_FAILURE_THRESHOLD, self.DEFAULT_ANALYSIS_WINDOW_HOURS, self.DEFAULT_COOLDOWN_HOURS)

    def _calculate_frequency(self, task_history: list) -> str:
        if not task_history:
            return "medium"
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        recent = [
            t for t in task_history
            if datetime.fromisoformat(t.get("start_time", "")) > cutoff
        ]
        count = len(recent)
        if count > self.HIGH_FREQUENCY_THRESHOLD:
            return "high"
        elif count < self.LOW_FREQUENCY_THRESHOLD:
            return "low"
        return "medium"

    def _is_critical_agent(self, agent_id: str) -> bool:
        keywords = ["critical", "prod", "production", "monitor"]
        if any(k in agent_id.lower() for k in keywords):
            return True
        if agent_id in self.config:
            return self.config[agent_id].get("is_critical", False)
        return False

    def set_manual_threshold(
        self,
        agent_id: str,
        failure_threshold: int = None,
        analysis_window_hours: int = None,
        cooldown_hours: int = None,
        is_critical: bool = None,
    ):
        """手动设置 Agent 阈值"""
        if agent_id not in self.config:
            self.config[agent_id] = {}
        if failure_threshold is not None:
            self.config[agent_id]["failure_threshold"] = failure_threshold
        if analysis_window_hours is not None:
            self.config[agent_id]["analysis_window_hours"] = analysis_window_hours
        if cooldown_hours is not None:
            self.config[agent_id]["cooldown_hours"] = cooldown_hours
        if is_critical is not None:
            self.config[agent_id]["is_critical"] = is_critical
        self._save_config()

    def get_agent_profile(self, agent_id: str, task_history: list) -> Dict:
        """获取 Agent 的完整配置"""
        frequency = self._calculate_frequency(task_history)
        is_critical = self._is_critical_agent(agent_id)
        threshold, window, cooldown = self.get_threshold(agent_id, task_history)

        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        recent = [
            t for t in task_history
            if datetime.fromisoformat(t.get("start_time", "")) > cutoff
        ]

        return {
            "agent_id": agent_id,
            "frequency": frequency,
            "is_critical": is_critical,
            "failure_threshold": threshold,
            "analysis_window_hours": window,
            "cooldown_hours": cooldown,
            "tasks_per_day": len(recent),
            "source": "manual" if agent_id in self.config else "auto",
        }

    def _load_config(self) -> Dict:
        if self.config_file and self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_config(self):
        if self.config_file:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
