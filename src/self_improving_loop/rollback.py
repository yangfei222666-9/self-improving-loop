"""
Auto Rollback - 自动回滚机制

当改进后效果变差时，自动回滚到上一个配置。

判断标准：
- 成功率下降 >10%
- 平均耗时增加 >20%
- 连续失败 ≥5 次

验证窗口：改进后 10 次任务
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class AutoRollback:
    """自动回滚管理器"""

    SUCCESS_RATE_DROP_THRESHOLD = 0.10
    LATENCY_INCREASE_THRESHOLD = 0.20
    CONSECUTIVE_FAILURES_THRESHOLD = 5
    VERIFICATION_WINDOW = 10

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.cwd() / "data" / "rollback"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_file = self.data_dir / "config_backups.jsonl"
        self.rollback_log = self.data_dir / "rollback_history.jsonl"

    def backup_config(self, agent_id: str, config: Dict, improvement_id: str) -> str:
        """备份配置，返回 backup_id"""
        backup_id = f"{agent_id}_{int(time.time())}"
        backup = {
            "backup_id": backup_id,
            "agent_id": agent_id,
            "improvement_id": improvement_id,
            "config": config,
            "timestamp": datetime.now().isoformat(),
        }
        with open(self.backup_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(backup, ensure_ascii=False) + "\n")
        return backup_id

    def should_rollback(
        self,
        agent_id: str,
        improvement_id: str,
        before_metrics: Dict,
        after_metrics: Dict,
    ) -> Tuple[bool, str]:
        """判断是否应该回滚，返回 (是否回滚, 原因)"""
        before_sr = before_metrics.get("success_rate", 0)
        after_sr = after_metrics.get("success_rate", 0)
        if before_sr > 0:
            drop = before_sr - after_sr
            if drop > self.SUCCESS_RATE_DROP_THRESHOLD:
                return True, f"成功率下降 {drop:.1%} (从 {before_sr:.1%} 到 {after_sr:.1%})"

        before_lat = before_metrics.get("avg_duration_sec", 0)
        after_lat = after_metrics.get("avg_duration_sec", 0)
        if before_lat > 0:
            increase = (after_lat - before_lat) / before_lat
            if increase > self.LATENCY_INCREASE_THRESHOLD:
                return True, f"平均耗时增加 {increase:.1%} (从 {before_lat:.1f}s 到 {after_lat:.1f}s)"

        consecutive = after_metrics.get("consecutive_failures", 0)
        if consecutive >= self.CONSECUTIVE_FAILURES_THRESHOLD:
            return True, f"连续失败 {consecutive} 次"

        return False, ""

    def rollback(self, agent_id: str, backup_id: str) -> Dict:
        """执行回滚"""
        backup = self._find_backup(backup_id)
        if not backup:
            return {"success": False, "error": f"Backup not found: {backup_id}"}

        try:
            entry = {
                "rollback_id": f"rollback_{int(time.time())}",
                "agent_id": agent_id,
                "backup_id": backup_id,
                "improvement_id": backup["improvement_id"],
                "timestamp": datetime.now().isoformat(),
                "config_restored": backup["config"],
            }
            with open(self.rollback_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return {
                "success": True,
                "backup_id": backup_id,
                "improvement_id": backup["improvement_id"],
                "config": backup["config"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _find_backup(self, backup_id: str) -> Optional[Dict]:
        if not self.backup_file.exists():
            return None
        with open(self.backup_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    backup = json.loads(line)
                    if backup["backup_id"] == backup_id:
                        return backup
        return None

    def get_rollback_history(self, agent_id: str = None) -> List[Dict]:
        if not self.rollback_log.exists():
            return []
        history = []
        with open(self.rollback_log, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if agent_id is None or entry["agent_id"] == agent_id:
                        history.append(entry)
        return history

    def get_stats(self) -> Dict:
        history = self.get_rollback_history()
        agents = set(e["agent_id"] for e in history)
        return {
            "total_rollbacks": len(history),
            "agents_rolled_back": len(agents),
            "agents": list(agents),
        }
