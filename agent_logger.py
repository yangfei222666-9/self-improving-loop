"""
Agent 评估与日志系统
统一指标：任务成功率、平均耗时、人工介入次数、失败恢复时间
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class AgentLogger:
    def __init__(self, workspace: str = "C:/Users/A/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.log_dir = self.workspace / "aios" / "agent_system" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_task(self, agent_id: str, task_data: Dict):
        """记录单次任务执行"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"{agent_id}_{today}.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "task_id": task_data.get("task_id"),
            "task_type": task_data.get("task_type"),
            "success": task_data.get("success", False),
            "duration_sec": task_data.get("duration_sec", 0),
            "human_intervention": task_data.get("human_intervention", False),
            "failure_recovery_sec": task_data.get("failure_recovery_sec", 0),
            "error_message": task_data.get("error_message"),
            "notes": task_data.get("notes"),
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_daily_stats(self, agent_id: str, date: Optional[str] = None) -> Dict:
        """获取某天的统计数据"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        log_file = self.log_dir / f"{agent_id}_{date}.jsonl"
        if not log_file.exists():
            return {
                "date": date,
                "agent_id": agent_id,
                "total_tasks": 0,
                "success_rate": 0.0,
                "avg_duration_sec": 0.0,
                "human_interventions": 0,
                "avg_recovery_sec": 0.0,
            }

        tasks = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    tasks.append(json.loads(line))

        total = len(tasks)
        successes = sum(1 for t in tasks if t["success"])
        interventions = sum(1 for t in tasks if t["human_intervention"])
        durations = [t["duration_sec"] for t in tasks if t["duration_sec"] > 0]
        recoveries = [
            t["failure_recovery_sec"] for t in tasks if t["failure_recovery_sec"] > 0
        ]

        return {
            "date": date,
            "agent_id": agent_id,
            "total_tasks": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_duration_sec": sum(durations) / len(durations) if durations else 0.0,
            "human_interventions": interventions,
            "avg_recovery_sec": (
                sum(recoveries) / len(recoveries) if recoveries else 0.0
            ),
        }

    def generate_daily_report(self, date: Optional[str] = None) -> str:
        """生成每日报告"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # 获取所有 Agent 的日志
        agent_ids = set()
        for log_file in self.log_dir.glob(f"*_{date}.jsonl"):
            agent_id = log_file.stem.rsplit("_", 1)[0]
            agent_ids.add(agent_id)

        report = [f"# Agent 日报 - {date}\n"]

        for agent_id in sorted(agent_ids):
            stats = self.get_daily_stats(agent_id, date)
            report.append(f"\n## {agent_id}")
            report.append(f"- 总任务数: {stats['total_tasks']}")
            report.append(f"- 成功率: {stats['success_rate']:.1%}")
            report.append(f"- 平均耗时: {stats['avg_duration_sec']:.1f}秒")
            report.append(f"- 人工介入: {stats['human_interventions']}次")
            if stats["avg_recovery_sec"] > 0:
                report.append(f"- 平均恢复时间: {stats['avg_recovery_sec']:.1f}秒")

        return "\n".join(report)


# CLI 接口
if __name__ == "__main__":
    import sys

    logger = AgentLogger()

    if len(sys.argv) < 2:
        print("Usage: python agent_logger.py [report|stats] [agent_id] [date]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "report":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        print(logger.generate_daily_report(date))

    elif command == "stats":
        if len(sys.argv) < 3:
            print("Usage: python agent_logger.py stats <agent_id> [date]")
            sys.exit(1)
        agent_id = sys.argv[2]
        date = sys.argv[3] if len(sys.argv) > 3 else None
        stats = logger.get_daily_stats(agent_id, date)
        print(json.dumps(stats, indent=2, ensure_ascii=False))
