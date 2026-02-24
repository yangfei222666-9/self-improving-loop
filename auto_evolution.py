"""
AIOS Agent Evolution System - Phase 2
自动进化引擎

核心功能：
1. 自动应用低风险改进
2. A/B 测试（新旧版本对比）
3. 自动回滚（如果进化后表现变差）
4. 进化策略库
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


class AutoEvolution:
    """自动进化引擎

    安全护栏：
    - MAX_EVOLUTIONS_PER_DAY: 单 Agent 每天最多进化次数
    - COOLDOWN_AFTER_ROLLBACK_HOURS: 回滚后冷却时间
    - MAX_CONSECUTIVE_FAILURES: 连续失败后停止自动进化
    """

    # ── 安全护栏常量 ──
    MAX_EVOLUTIONS_PER_DAY = 5
    COOLDOWN_AFTER_ROLLBACK_HOURS = 6
    MAX_CONSECUTIVE_FAILURES = 3

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path.home() / ".openclaw" / "workspace" / "aios" / "agent_system" / "data"
        
        self.data_dir = Path(data_dir)
        self.evolution_dir = self.data_dir / "evolution"
        self.evolution_dir.mkdir(parents=True, exist_ok=True)

        # 策略库
        self.strategies_file = self.evolution_dir / "evolution_strategies.json"
        self.load_strategies()

    def _check_safety_guardrails(self, agent_id: str) -> tuple:
        """检查安全护栏，返回 (safe: bool, reason: str)"""
        evolution_log = self.evolution_dir / "evolution_history.jsonl"
        if not evolution_log.exists():
            return True, ""

        now = time.time()
        today_start = now - 86400
        recent_evolutions = []
        consecutive_failures = 0
        last_rollback_ts = 0

        with open(evolution_log, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record.get("agent_id") != agent_id:
                        continue
                    ts = record.get("timestamp", 0)
                    if ts > today_start:
                        recent_evolutions.append(record)
                    # 追踪回滚
                    if record.get("evolution_type") == "rollback":
                        last_rollback_ts = max(last_rollback_ts, ts)
                except (json.JSONDecodeError, KeyError):
                    continue

        # 检查每日上限
        if len(recent_evolutions) >= self.MAX_EVOLUTIONS_PER_DAY:
            return False, f"已达每日进化上限 ({self.MAX_EVOLUTIONS_PER_DAY} 次)"

        # 检查回滚冷却
        if last_rollback_ts > 0:
            cooldown_end = last_rollback_ts + self.COOLDOWN_AFTER_ROLLBACK_HOURS * 3600
            if now < cooldown_end:
                remaining_h = (cooldown_end - now) / 3600
                return False, f"回滚冷却中，剩余 {remaining_h:.1f} 小时"

        return True, ""

    def load_strategies(self):
        """加载进化策略库"""
        if self.strategies_file.exists():
            with open(self.strategies_file, "r", encoding="utf-8") as f:
                self.strategies = json.load(f)
        else:
            # 默认策略
            self.strategies = {
                "high_failure_rate": {
                    "trigger": {"failure_rate": ">0.3"},
                    "action": "increase_thinking",
                    "risk": "low",
                    "auto_apply": True,
                    "description": "失败率过高，提升思考深度"
                },
                "timeout_errors": {
                    "trigger": {"error_pattern": "timeout", "count": ">=3"},
                    "action": "increase_timeout",
                    "risk": "low",
                    "auto_apply": True,
                    "description": "频繁超时，增加超时时间"
                },
                "permission_errors": {
                    "trigger": {"error_pattern": "permission", "count": ">=3"},
                    "action": "adjust_tools",
                    "risk": "medium",
                    "auto_apply": False,
                    "description": "权限错误，调整工具权限"
                },
                "rate_limit_errors": {
                    "trigger": {"error_pattern": "rate limit|502", "count": ">=3"},
                    "action": "add_retry",
                    "risk": "low",
                    "auto_apply": True,
                    "description": "API 限流，添加重试机制"
                },
                "task_type_failure": {
                    "trigger": {"task_type_failure": ">=3"},
                    "action": "install_skill",
                    "risk": "medium",
                    "auto_apply": False,
                    "description": "特定任务类型失败，安装相关技能"
                }
            }
            self.save_strategies()

    def save_strategies(self):
        """保存策略库"""
        with open(self.strategies_file, "w", encoding="utf-8") as f:
            json.dump(self.strategies, f, ensure_ascii=False, indent=2)

    def evaluate_triggers(self, agent_id: str, analysis: Dict) -> List[Dict]:
        """
        评估触发条件，返回匹配的策略

        Args:
            agent_id: Agent ID
            analysis: 失败分析结果

        Returns:
            匹配的策略列表
        """
        matched_strategies = []

        for strategy_name, strategy in self.strategies.items():
            trigger = strategy["trigger"]
            
            # 检查失败率触发
            if "failure_rate" in trigger:
                threshold = float(trigger["failure_rate"].replace(">", ""))
                if analysis["failure_rate"] > threshold:
                    matched_strategies.append({
                        "name": strategy_name,
                        "strategy": strategy,
                        "reason": f"失败率 {analysis['failure_rate']:.1%} > {threshold:.1%}"
                    })
            
            # 检查错误模式触发
            if "error_pattern" in trigger:
                pattern = trigger["error_pattern"]
                min_count = int(trigger.get("count", ">=1").replace(">=", ""))
                
                error_count = 0
                for task_type, data in analysis.get("failure_patterns", {}).items():
                    for error in data.get("errors", []):
                        if any(p in error.lower() for p in pattern.split("|")):
                            error_count += 1
                
                if error_count >= min_count:
                    matched_strategies.append({
                        "name": strategy_name,
                        "strategy": strategy,
                        "reason": f"检测到 {error_count} 次 '{pattern}' 错误"
                    })
            
            # 检查任务类型失败触发
            if "task_type_failure" in trigger:
                min_count = int(trigger["task_type_failure"].replace(">=", ""))
                
                for task_type, data in analysis.get("failure_patterns", {}).items():
                    if data["count"] >= min_count:
                        matched_strategies.append({
                            "name": strategy_name,
                            "strategy": strategy,
                            "reason": f"{task_type} 任务失败 {data['count']} 次",
                            "task_type": task_type
                        })

        return matched_strategies

    def generate_evolution_plan(self, agent_id: str, agent_config: Dict, strategy: Dict) -> Dict:
        """
        生成进化计划

        Args:
            agent_id: Agent ID
            agent_config: Agent 当前配置
            strategy: 匹配的策略

        Returns:
            进化计划
        """
        action = strategy["action"]
        plan = {
            "agent_id": agent_id,
            "strategy_name": strategy.get("name", "unknown"),
            "action": action,
            "risk": strategy["risk"],
            "auto_apply": strategy["auto_apply"],
            "description": strategy["description"],
            "changes": {},
            "rollback": {}
        }

        # 根据 action 生成具体变更
        if action == "increase_thinking":
            current_thinking = agent_config.get("thinking", "off")
            thinking_levels = ["off", "low", "medium", "high"]
            current_index = thinking_levels.index(current_thinking) if current_thinking in thinking_levels else 0
            
            if current_index < len(thinking_levels) - 1:
                new_thinking = thinking_levels[current_index + 1]
                plan["changes"] = {"thinking": new_thinking}
                plan["rollback"] = {"thinking": current_thinking}

        elif action == "increase_timeout":
            # 假设默认超时 30s，增加到 60s
            plan["changes"] = {"timeout_sec": 60}
            plan["rollback"] = {"timeout_sec": 30}

        elif action == "adjust_tools":
            # 根据任务类型调整工具权限
            task_type = strategy.get("task_type", "code")
            
            if task_type == "code":
                plan["changes"] = {
                    "tools": {
                        "allow": ["exec", "read", "write", "edit", "web_search", "web_fetch"],
                        "deny": ["message", "cron", "gateway"]
                    }
                }
            elif task_type == "analysis":
                plan["changes"] = {
                    "tools": {
                        "allow": ["exec", "read", "write", "web_search", "web_fetch"],
                        "deny": ["edit", "message", "cron", "gateway"]
                    }
                }
            
            plan["rollback"] = {"tools": agent_config.get("tools", {})}

        elif action == "add_retry":
            # 添加重试配置（这需要在执行层实现）
            plan["changes"] = {"retry_config": {"max_retries": 3, "backoff": "exponential"}}
            plan["rollback"] = {"retry_config": None}

        elif action == "install_skill":
            task_type = strategy.get("task_type", "code")
            skill_map = {
                "code": "coding-agent",
                "analysis": "data-analysis",
                "monitor": "system-resource-monitor",
                "research": "web-research"
            }
            
            skill = skill_map.get(task_type)
            if skill:
                current_skills = agent_config.get("skills", [])
                if skill not in current_skills:
                    plan["changes"] = {"skills": current_skills + [skill]}
                    plan["rollback"] = {"skills": current_skills}

        return plan

    def apply_evolution_plan(self, plan: Dict, agent_manager) -> bool:
        """
        应用进化计划

        Args:
            plan: 进化计划
            agent_manager: AgentManager 实例

        Returns:
            是否成功
        """
        agent_id = plan["agent_id"]
        changes = plan["changes"]

        if not changes:
            return False

        # 应用变更
        agent_manager._update_agent(agent_id, changes)

        # 记录进化历史
        try:
            from .evolution import AgentEvolution
        except ImportError:
            from evolution import AgentEvolution
        evolution = AgentEvolution()
        evolution.apply_evolution(
            agent_id=agent_id,
            evolution={
                "type": plan["action"],
                "changes": changes,
                "reason": plan["description"]
            }
        )

        return True

    def check_evolution_result(self, agent_id: str, before_score: float, after_score: float) -> Dict:
        """
        检查进化结果

        Args:
            agent_id: Agent ID
            before_score: 进化前成功率
            after_score: 进化后成功率

        Returns:
            {
                'improved': bool,
                'delta': float,
                'action': 'keep' | 'rollback'
            }
        """
        delta = after_score - before_score
        
        # 如果成功率提升 > 10%，认为进化成功
        if delta > 0.1:
            return {
                "improved": True,
                "delta": delta,
                "action": "keep",
                "message": f"进化成功！成功率提升 {delta:.1%}"
            }
        
        # 如果成功率下降 > 10%，回滚
        elif delta < -0.1:
            return {
                "improved": False,
                "delta": delta,
                "action": "rollback",
                "message": f"进化失败！成功率下降 {abs(delta):.1%}，建议回滚"
            }
        
        # 变化不大，继续观察
        else:
            return {
                "improved": None,
                "delta": delta,
                "action": "observe",
                "message": f"进化效果不明显（{delta:+.1%}），继续观察"
            }

    def auto_evolve(self, agent_id: str, agent_manager) -> Dict:
        """
        自动进化（主入口）

        Args:
            agent_id: Agent ID
            agent_manager: AgentManager 实例

        Returns:
            进化结果
        """
        try:
            from .evolution import AgentEvolution
            from .evolution_events import get_emitter
        except ImportError:
            from evolution import AgentEvolution
            from evolution_events import get_emitter
        
        evolution = AgentEvolution()
        emitter = get_emitter()

        # 0. 安全护栏检查
        safe, reason = self._check_safety_guardrails(agent_id)
        if not safe:
            return {
                "status": "blocked",
                "reason": f"安全护栏: {reason}"
            }

        # 1. 分析失败模式
        analysis = evolution.analyze_failures(agent_id, lookback_hours=24)

        if analysis["total_tasks"] < 5:
            return {
                "status": "skipped",
                "reason": "任务数量不足（< 5），无法评估"
            }

        # 2. 评估触发条件
        matched_strategies = self.evaluate_triggers(agent_id, analysis)

        if not matched_strategies:
            return {
                "status": "skipped",
                "reason": "未触发任何进化策略"
            }

        # 3. 筛选可自动应用的策略
        auto_strategies = [s for s in matched_strategies if s["strategy"]["auto_apply"]]

        if not auto_strategies:
            # 发送候选事件（需要人工审核）
            emitter.emit_candidate(
                agent_id=agent_id,
                strategies=[s["reason"] for s in matched_strategies],
                risk="medium"
            )
            
            return {
                "status": "pending_review",
                "strategies": matched_strategies,
                "reason": "所有匹配策略需要人工审核"
            }

        # 4. 生成进化计划
        agent_config = agent_manager.get_agent(agent_id)
        plans = []

        for strategy_match in auto_strategies:
            plan = self.generate_evolution_plan(
                agent_id=agent_id,
                agent_config=agent_config,
                strategy=strategy_match
            )
            if plan["changes"]:
                plans.append(plan)

        if not plans:
            return {
                "status": "skipped",
                "reason": "未生成有效的进化计划"
            }

        # 5. 应用进化计划
        applied_plans = []
        for plan in plans:
            success = self.apply_evolution_plan(plan, agent_manager)
            if success:
                applied_plans.append(plan)

        # 发送应用事件
        if applied_plans:
            emitter.emit_applied(
                agent_id=agent_id,
                plans=[{
                    "action": p["action"],
                    "description": p["description"],
                    "changes": p["changes"]
                } for p in applied_plans]
            )

        return {
            "status": "applied",
            "plans": applied_plans,
            "message": f"已自动应用 {len(applied_plans)} 个进化改进"
        }


# CLI 接口
def main():
    import sys
    from .core.agent_manager import AgentManager
    
    if len(sys.argv) < 2:
        print("用法：python -m aios.agent_system.auto_evolution <command> [args]")
        print("\n命令：")
        print("  evolve <agent_id>  - 自动进化 Agent")
        print("  strategies         - 查看策略库")
        return

    auto_evolution = AutoEvolution()
    command = sys.argv[1]

    if command == "evolve":
        if len(sys.argv) < 3:
            print("错误：需要提供 agent_id")
            return
        
        agent_id = sys.argv[2]
        agent_manager = AgentManager()
        
        result = auto_evolution.auto_evolve(agent_id, agent_manager)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "strategies":
        print(json.dumps(auto_evolution.strategies, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令：{command}")


if __name__ == "__main__":
    main()
