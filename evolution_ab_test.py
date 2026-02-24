"""
AIOS Evolution A/B Testing - 简化版窗口对比

不用复杂实验框架，v0.6 用最小 A/B（实际上是 before/after）就够：
- Before 窗口：应用前最近 N 个任务（如 20）
- After 窗口：应用后最近 N 个任务（如 20）
- 指标：success_rate、timeout_count、rate_limit_count、avg_latency（可选）
"""

import json
from pathlib import Path
from typing import Dict, List


class EvolutionABTest:
    """进化 A/B 测试（窗口对比）"""

    def __init__(self):
        self.data_dir = Path.home() / ".openclaw" / "workspace" / "aios" / "agent_system" / "data" / "evolution"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def calculate_window_metrics(self, tasks: List[Dict]) -> Dict:
        """
        计算窗口指标

        Args:
            tasks: 任务列表

        Returns:
            {
                'success_rate': float,
                'timeout_count': int,
                'rate_limit_count': int,
                'avg_latency': float
            }
        """
        if not tasks:
            return {
                "success_rate": 0.0,
                "timeout_count": 0,
                "rate_limit_count": 0,
                "avg_latency": 0.0
            }

        success_count = sum(1 for t in tasks if t.get("success", False))
        timeout_count = sum(1 for t in tasks if "timeout" in t.get("error", "").lower())
        rate_limit_count = sum(1 for t in tasks if "rate limit" in t.get("error", "").lower() or "502" in t.get("error", ""))
        
        total_latency = sum(t.get("duration_sec", 0) for t in tasks)
        avg_latency = total_latency / len(tasks) if tasks else 0

        return {
            "success_rate": success_count / len(tasks),
            "timeout_count": timeout_count,
            "rate_limit_count": rate_limit_count,
            "avg_latency": avg_latency
        }

    def should_rollback(self, before: Dict, after: Dict) -> bool:
        """
        判断是否应该回滚（保守版）

        Args:
            before: 应用前指标
            after: 应用后指标

        Returns:
            是否应该回滚
        """
        # 成功率下降 ≥ 5%
        if after["success_rate"] < before["success_rate"] - 0.05:
            return True
        
        # 超时增加 ≥ 2 次
        if after["timeout_count"] >= before["timeout_count"] + 2:
            return True
        
        # 综合评分下降 ≥ 0.05
        before_score = before["success_rate"] - (before["timeout_count"] * 0.01) - (before["rate_limit_count"] * 0.01)
        after_score = after["success_rate"] - (after["timeout_count"] * 0.01) - (after["rate_limit_count"] * 0.01)
        
        if after_score < before_score - 0.05:
            return True
        
        return False

    def evaluate_evolution(self, agent_id: str, evolution_timestamp: int, window_size: int = 20) -> Dict:
        """
        评估进化效果

        Args:
            agent_id: Agent ID
            evolution_timestamp: 进化时间戳
            window_size: 窗口大小（任务数）

        Returns:
            {
                'before': {...},
                'after': {...},
                'should_rollback': bool,
                'reason': str
            }
        """
        from .evolution import AgentEvolution
        
        evolution = AgentEvolution()
        
        # 获取进化前后的任务
        all_tasks = evolution._load_task_executions(agent_id)
        
        before_tasks = [t for t in all_tasks if t["timestamp"] < evolution_timestamp][-window_size:]
        after_tasks = [t for t in all_tasks if t["timestamp"] >= evolution_timestamp][:window_size]
        
        if len(after_tasks) < window_size:
            return {
                "status": "insufficient_data",
                "reason": f"应用后任务数不足（{len(after_tasks)} < {window_size}），无法评估"
            }
        
        # 计算指标
        before_metrics = self.calculate_window_metrics(before_tasks)
        after_metrics = self.calculate_window_metrics(after_tasks)
        
        # 判断是否回滚
        should_rollback = self.should_rollback(before_metrics, after_metrics)
        
        # 生成原因
        if should_rollback:
            reasons = []
            if after_metrics["success_rate"] < before_metrics["success_rate"] - 0.05:
                delta = (before_metrics["success_rate"] - after_metrics["success_rate"]) * 100
                reasons.append(f"成功率下降 {delta:.1f}%")
            if after_metrics["timeout_count"] >= before_metrics["timeout_count"] + 2:
                delta = after_metrics["timeout_count"] - before_metrics["timeout_count"]
                reasons.append(f"超时增加 {delta} 次")
            
            reason = "、".join(reasons)
        else:
            delta = (after_metrics["success_rate"] - before_metrics["success_rate"]) * 100
            if delta > 5:
                reason = f"成功率提升 {delta:.1f}%，进化成功"
            elif delta > 0:
                reason = f"成功率略有提升（{delta:.1f}%），继续观察"
            else:
                reason = "效果不明显，继续观察"
        
        return {
            "status": "evaluated",
            "before": before_metrics,
            "after": after_metrics,
            "should_rollback": should_rollback,
            "reason": reason
        }


# CLI 接口
def main():
    import sys
    
    if len(sys.argv) < 3:
        print("用法：python -m aios.agent_system.evolution_ab_test <agent_id> <evolution_timestamp>")
        return
    
    agent_id = sys.argv[1]
    evolution_timestamp = int(sys.argv[2])
    
    ab_test = EvolutionABTest()
    result = ab_test.evaluate_evolution(agent_id, evolution_timestamp)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
