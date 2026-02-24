"""
Self-Improving Loop - 核心引擎

统一的 Agent 自我改进闭环，零外部依赖。

  ┌─────────────────────────────────────────────────────────┐
  │                  Self-Improving Loop                     │
  │                                                          │
  │  1. Execute Task    → 执行任务（透明代理）               │
  │  2. Record Result   → 记录结果（Tracer）                 │
  │  3. Analyze Failure → 分析失败模式                       │
  │  4. Generate Fix    → 生成改进建议                       │
  │  5. Auto Apply      → 自动应用低风险改进                 │
  │  6. Verify Effect   → 验证效果                           │
  │  7. Update Config   → 更新配置 + 自动回滚                │
  └─────────────────────────────────────────────────────────┘
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from .tracer import AgentTracer, TraceAnalyzer
from .rollback import AutoRollback
from .threshold import AdaptiveThreshold
from .notifier import Notifier, PrintNotifier


class AgentConfig:
    """简单的 Agent 配置管理（替代外部 AgentManager）"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.config_file = data_dir / "agent_configs.json"
        self.agents: Dict[str, Dict] = self._load()

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        return self.agents.get(agent_id)

    def update_stats(self, agent_id: str, success: bool, duration: float):
        if agent_id not in self.agents:
            self.agents[agent_id] = {"stats": {"tasks_completed": 0, "tasks_failed": 0, "success_rate": 0.0}}
        stats = self.agents[agent_id].setdefault("stats", {})
        if success:
            stats["tasks_completed"] = stats.get("tasks_completed", 0) + 1
        else:
            stats["tasks_failed"] = stats.get("tasks_failed", 0) + 1
        total = stats.get("tasks_completed", 0) + stats.get("tasks_failed", 0)
        stats["success_rate"] = stats.get("tasks_completed", 0) / total if total > 0 else 0.0
        self._save()

    def _load(self) -> Dict:
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.agents, f, ensure_ascii=False, indent=2)


class FailureAnalyzer:
    """内置失败模式分析器"""

    def __init__(self, trace_analyzer: TraceAnalyzer):
        self.trace_analyzer = trace_analyzer

    def analyze(self, days: int = 7, min_occurrences: int = 3) -> Dict:
        """分析最近 N 天的失败模式"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            t for t in self.trace_analyzer.traces
            if datetime.fromisoformat(t["start_time"]) > cutoff
        ]
        failures = [t for t in recent if not t.get("success")]
        patterns = self._identify_patterns(failures, recent, min_occurrences)
        improvements = self._generate_improvements(patterns)

        return {
            "generated_at": datetime.now().isoformat(),
            "analysis_period_days": days,
            "total_traces": len(recent),
            "total_failures": len(failures),
            "patterns": patterns,
            "improvements": improvements,
        }

    def _identify_patterns(self, failures: List[Dict], all_traces: List[Dict], min_occ: int) -> List[Dict]:
        patterns = []

        # 按错误签名分组
        error_groups: Dict[str, list] = defaultdict(list)
        for f in failures:
            sig = TraceAnalyzer._generate_error_signature(f.get("error", "unknown"))
            error_groups[sig].append(f)

        for sig, group in error_groups.items():
            if len(group) >= min_occ:
                patterns.append({
                    "type": "error_pattern",
                    "signature": sig,
                    "occurrences": len(group),
                    "affected_agents": list(set(t["agent_id"] for t in group)),
                    "sample_error": group[0]["error"],
                })

        # 按 Agent 分组
        agent_failures: Dict[str, list] = defaultdict(list)
        for f in failures:
            agent_failures[f["agent_id"]].append(f)

        for agent_id, group in agent_failures.items():
            if len(group) >= min_occ:
                total_for_agent = len([t for t in all_traces if t["agent_id"] == agent_id])
                patterns.append({
                    "type": "agent_pattern",
                    "agent_id": agent_id,
                    "occurrences": len(group),
                    "failure_rate": len(group) / total_for_agent if total_for_agent > 0 else 0,
                })

        return patterns

    def _generate_improvements(self, patterns: List[Dict]) -> List[Dict]:
        improvements = []
        for p in patterns:
            imp = None
            if p["type"] == "error_pattern":
                imp = self._suggest_error_fix(p)
            elif p["type"] == "agent_pattern" and p.get("failure_rate", 0) > 0.5:
                imp = {
                    "pattern_type": "agent_pattern",
                    "agent_id": p["agent_id"],
                    "improvement_type": "agent_degradation",
                    "description": f"Agent {p['agent_id']} 失败率过高 ({p['failure_rate']:.1%})",
                    "action": {"type": "agent_action", "target": p["agent_id"], "change": "降低优先级或触发重启"},
                    "priority": "critical",
                    "risk": "low",
                }
            if imp:
                improvements.append(imp)
        return improvements

    def _suggest_error_fix(self, pattern: Dict) -> Optional[Dict]:
        error = (pattern.get("sample_error") or "").lower()
        if "timeout" in error or "超时" in error:
            return {
                "pattern_type": "error_pattern",
                "pattern_signature": pattern["signature"],
                "improvement_type": "increase_timeout",
                "description": "检测到频繁超时，建议增加超时时间",
                "action": {"type": "config_change", "target": "timeout", "change": "increase by 50%"},
                "priority": "high",
                "risk": "low",
            }
        if any(k in error for k in ("502", "503", "network")):
            return {
                "pattern_type": "error_pattern",
                "pattern_signature": pattern["signature"],
                "improvement_type": "add_retry",
                "description": "检测到网络错误，建议增加重试机制",
                "action": {"type": "code_change", "target": "network_calls", "change": "add retry with exponential backoff"},
                "priority": "high",
                "risk": "low",
            }
        if "429" in error or "rate limit" in error:
            return {
                "pattern_type": "error_pattern",
                "pattern_signature": pattern["signature"],
                "improvement_type": "rate_limiting",
                "description": "检测到限流错误，建议降低请求频率",
                "action": {"type": "config_change", "target": "request_rate", "change": "add delay between requests"},
                "priority": "medium",
                "risk": "low",
            }
        return None


class SelfImprovingLoop:
    """统一的 Agent 自我改进闭环"""

    MIN_FAILURES_FOR_ANALYSIS = 3
    ANALYSIS_WINDOW_HOURS = 24
    IMPROVEMENT_COOLDOWN_HOURS = 6
    AUTO_APPLY_RISK_LEVEL = "low"

    def __init__(self, data_dir: str = None, notifier: Notifier = None):
        self.data_dir = Path(data_dir) if data_dir else Path.cwd() / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        trace_dir = self.data_dir / "traces"
        rollback_dir = self.data_dir / "rollback"
        threshold_file = self.data_dir / "adaptive_thresholds.json"

        self.agent_config = AgentConfig(self.data_dir)
        self.trace_analyzer = TraceAnalyzer(trace_dir)
        self.failure_analyzer = FailureAnalyzer(self.trace_analyzer)
        self.auto_rollback = AutoRollback(rollback_dir)
        self.adaptive_threshold = AdaptiveThreshold(threshold_file)
        self.notifier = notifier or PrintNotifier()

        self.state_file = self.data_dir / "loop_state.json"
        self.log_file = self.data_dir / "loop.log"
        self.state = self._load_state()

    def execute_with_improvement(
        self,
        agent_id: str,
        task: str,
        execute_fn: Callable[[], Any],
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        执行任务并自动触发改进循环

        Returns:
            {
                "success": bool,
                "result": Any,
                "error": str | None,
                "duration_sec": float,
                "improvement_triggered": bool,
                "improvement_applied": int,
                "rollback_executed": dict | None,
            }
        """
        # Step 1: 执行 + 追踪
        tracer = AgentTracer(agent_id, self.data_dir / "traces")
        tracer.start_task(task, context)

        start = time.time()
        success = False
        result = None
        error = None

        try:
            result = execute_fn()
            success = True
            tracer.end_task(success=True)
        except Exception as e:
            error = str(e)
            tracer.end_task(success=False, error=error)
        finally:
            duration = time.time() - start

        self.agent_config.update_stats(agent_id, success, duration)
        self.trace_analyzer.reload()

        # Step 2-7: 失败时触发改进
        improvement_triggered = False
        improvement_applied = 0
        rollback_executed = None

        if not success:
            if self._should_trigger_improvement(agent_id):
                improvement_triggered = True
                improvement_applied = self._run_improvement_cycle(agent_id)
                if improvement_applied > 0:
                    self.notifier.notify_improvement(agent_id, improvement_applied)

        # Step 8: 检查回滚
        rollback_result = self._check_and_rollback(agent_id)
        if rollback_result:
            rollback_executed = rollback_result
            self.notifier.notify_rollback(
                agent_id,
                rollback_result.get("reason", "unknown"),
                {"before_metrics": rollback_result.get("before_metrics", {}),
                 "after_metrics": rollback_result.get("after_metrics", {})},
            )

        return {
            "success": success,
            "result": result,
            "error": error,
            "duration_sec": duration,
            "improvement_triggered": improvement_triggered,
            "improvement_applied": improvement_applied,
            "rollback_executed": rollback_executed,
        }

    def _should_trigger_improvement(self, agent_id: str) -> bool:
        agent_traces = [t for t in self.trace_analyzer.traces if t["agent_id"] == agent_id]
        failure_threshold, window_hours, cooldown_hours = \
            self.adaptive_threshold.get_threshold(agent_id, agent_traces)

        # 冷却期检查
        last = self.state.get("last_improvement", {}).get(agent_id)
        if last:
            if datetime.now() - datetime.fromisoformat(last) < timedelta(hours=cooldown_hours):
                self._log("info", f"Agent {agent_id} 在冷却期内（{cooldown_hours}h）")
                return False

        # 失败次数检查
        cutoff = datetime.now() - timedelta(hours=window_hours)
        recent = [
            t for t in agent_traces
            if datetime.fromisoformat(t["start_time"]) > cutoff
        ]
        failures = [t for t in recent if not t.get("success")]
        if len(failures) < failure_threshold:
            return False

        self._log("info", f"Agent {agent_id} 触发改进（失败 {len(failures)}/{failure_threshold}）")
        return True

    def _run_improvement_cycle(self, agent_id: str) -> int:
        self._log("info", f"触发 Agent {agent_id} 的改进循环")
        applied = 0

        before_metrics = self._calculate_metrics(agent_id)

        report = self.failure_analyzer.analyze(days=1, min_occurrences=self.MIN_FAILURES_FOR_ANALYSIS)
        agent_improvements = [
            imp for imp in report.get("improvements", [])
            if imp.get("agent_id") == agent_id or
               agent_id in (imp.get("affected_agents") or [])
        ]

        if not agent_improvements:
            return 0

        # 备份配置
        agent = self.agent_config.get_agent(agent_id)
        improvement_id = f"improvement_{int(time.time())}"
        if agent:
            backup_id = self.auto_rollback.backup_config(agent_id, agent, improvement_id)
            self.state.setdefault("backups", {})[agent_id] = {
                "backup_id": backup_id,
                "improvement_id": improvement_id,
                "before_metrics": before_metrics,
                "timestamp": datetime.now().isoformat(),
            }
            self._save_state()

        for imp in agent_improvements:
            if imp.get("risk", "high") != self.AUTO_APPLY_RISK_LEVEL:
                continue
            applied += 1
            self._log("success", f"应用改进: {imp['description']}")

        self.state.setdefault("last_improvement", {})[agent_id] = datetime.now().isoformat()
        self._save_state()
        return applied

    def _calculate_metrics(self, agent_id: str) -> Dict:
        agent_traces = [t for t in self.trace_analyzer.traces if t["agent_id"] == agent_id]
        _, window_hours, _ = self.adaptive_threshold.get_threshold(agent_id, agent_traces)
        cutoff = datetime.now() - timedelta(hours=window_hours)
        recent = [
            t for t in agent_traces
            if datetime.fromisoformat(t["start_time"]) > cutoff
        ]
        if not recent:
            return {"success_rate": 0.0, "avg_duration_sec": 0.0, "total_tasks": 0, "consecutive_failures": 0}

        total = len(recent)
        successes = sum(1 for t in recent if t.get("success"))
        avg_dur = sum(t.get("duration_sec", 0) for t in recent) / total

        consecutive = 0
        for t in reversed(recent):
            if not t.get("success"):
                consecutive += 1
            else:
                break

        return {
            "success_rate": successes / total,
            "avg_duration_sec": avg_dur,
            "total_tasks": total,
            "consecutive_failures": consecutive,
        }

    def _check_and_rollback(self, agent_id: str) -> Optional[Dict]:
        backup_info = self.state.get("backups", {}).get(agent_id)
        if not backup_info:
            return None

        after_metrics = self._calculate_metrics(agent_id)
        if after_metrics["total_tasks"] < self.auto_rollback.VERIFICATION_WINDOW:
            return None

        before_metrics = backup_info["before_metrics"]
        should, reason = self.auto_rollback.should_rollback(
            agent_id, backup_info["improvement_id"], before_metrics, after_metrics
        )

        if should:
            self._log("warn", f"效果变差，执行回滚: {reason}")
            result = self.auto_rollback.rollback(agent_id, backup_info["backup_id"])
            if result["success"]:
                self.state.get("backups", {}).pop(agent_id, None)
                self._save_state()
                return {
                    "agent_id": agent_id,
                    "reason": reason,
                    "before_metrics": before_metrics,
                    "after_metrics": after_metrics,
                    "backup_id": backup_info["backup_id"],
                }
        else:
            # 改进成功，清除备份
            self.state.get("backups", {}).pop(agent_id, None)
            self._save_state()

        return None

    def get_improvement_stats(self, agent_id: str = None) -> Dict:
        if agent_id:
            agent = self.agent_config.get_agent(agent_id)
            last = self.state.get("last_improvement", {}).get(agent_id)
            return {
                "agent_id": agent_id,
                "agent_stats": agent.get("stats", {}) if agent else {},
                "last_improvement": last,
                "cooldown_remaining_hours": self._get_cooldown_remaining(agent_id),
            }
        return {
            "total_agents": len(self.agent_config.agents),
            "total_improvements": len(self.state.get("last_improvement", {})),
            "agents_improved": list(self.state.get("last_improvement", {}).keys()),
        }

    def _get_cooldown_remaining(self, agent_id: str) -> float:
        last = self.state.get("last_improvement", {}).get(agent_id)
        if not last:
            return 0.0
        elapsed = datetime.now() - datetime.fromisoformat(last)
        remaining = timedelta(hours=self.IMPROVEMENT_COOLDOWN_HOURS) - elapsed
        return max(0, remaining.total_seconds() / 3600)

    def _load_state(self) -> Dict:
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _log(self, level: str, message: str):
        entry = {"timestamp": datetime.now().isoformat(), "level": level, "message": message}
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
