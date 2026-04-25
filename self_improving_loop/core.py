"""
Self-Improving Loop - Core

完整的 7 步自我改进闭环
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional

from .adapters import ConfigAdapter
from .rollback import AutoRollback
from .threshold import AdaptiveThreshold
from .notifier import TelegramNotifier
from .time_utils import parse_trace_timestamp
from .trace_store import JsonlTraceStore, SQLiteTraceStore


class SelfImprovingLoop:
    """统一的 Agent 自我改进闭环"""

    def __init__(
        self,
        data_dir: str = None,
        notifier: Optional[TelegramNotifier] = None,
        improvement_strategy: Optional[Any] = None,
        config_adapter: Optional[ConfigAdapter] = None,
        storage: str = "jsonl",
    ):
        """
        Args:
            data_dir: where traces/state/backups live. Defaults to
                ``~/.self-improving-loop/data``.
            notifier: any subclass of TelegramNotifier (override
                ``_send_message``) to route events to Slack / Discord /
                email / etc. Defaults to a stdout-logging stub.
            improvement_strategy: optional duck-typed strategy with
                ``analyze(agent_id=..., traces=..., before_metrics=...)``,
                and, for legacy compatibility, optional ``apply`` /
                ``current_config`` / ``rollback`` methods. Without it the loop
                tracks and triggers, but does not pretend to mutate config.
            config_adapter: optional ConfigAdapter that owns real config IO:
                ``get_config`` before a patch, ``apply_config`` for guarded
                changes, and ``rollback_config`` when regression is detected.
            storage: trace storage backend. ``"jsonl"`` keeps transparent
                append-only files; ``"sqlite"`` uses a WAL-enabled SQLite DB
                for multi-worker deployments. Both are stdlib-only.
        """
        if data_dir is None:
            data_dir = Path.home() / ".self-improving-loop" / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化子模块
        self.auto_rollback = AutoRollback(str(self.data_dir))
        self.adaptive_threshold = AdaptiveThreshold(str(self.data_dir))
        self.notifier = notifier or TelegramNotifier(enabled=True)
        self.improvement_strategy = improvement_strategy
        self.config_adapter = config_adapter
        self.storage = storage
        # alias for the README-facing name
        self.rollback = self.auto_rollback

        # 状态文件
        self.state_file = self.data_dir / "loop_state.json"
        self.log_file = self.data_dir / "loop.log"
        self.traces_file = self.data_dir / "traces.jsonl"
        self.trace_db_file = self.data_dir / "traces.sqlite3"
        if storage == "jsonl":
            self.trace_store = JsonlTraceStore(self.traces_file)
        elif storage == "sqlite":
            self.trace_store = SQLiteTraceStore(self.trace_db_file)
        else:
            raise ValueError("storage must be 'jsonl' or 'sqlite'")

        # 加载状态
        self.state = self._load_state()

    def execute_with_improvement(
        self,
        agent_id: str,
        task: str,
        execute_fn: Callable[[], Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行任务并自动触发改进循环

        Args:
            agent_id: Agent ID
            task: 任务描述
            execute_fn: 任务执行函数（返回任意结果）
            context: 任务上下文（可选）

        Returns:
            {
                "success": bool,
                "result": Any,
                "error": str,
                "duration_sec": float,
                "improvement_triggered": bool,
                "improvement_applied": int,
                "rollback_executed": Optional[Dict]
            }
        """
        # Step 1: 执行任务 + 记录追踪
        start_time = time.time()
        success = False
        result = None
        error = None

        try:
            result = execute_fn()
            success = True
        except Exception as e:
            error = str(e)
        finally:
            duration = time.time() - start_time

        # 记录追踪
        self._record_trace(agent_id, task, success, duration, error, context)

        # Step 2-7: 如果失败，触发改进循环
        improvement_triggered = False
        improvement_applied = 0
        rollback_executed = None

        if not success:
            should_improve = self._should_trigger_improvement(agent_id)
            if should_improve:
                improvement_triggered = True
                improvement_applied = self._run_improvement_cycle(agent_id)

                # 发送改进通知
                if improvement_applied > 0:
                    self.notifier.notify_improvement(
                        agent_id=agent_id,
                        improvements_applied=improvement_applied
                    )

        # Step 8: 检查是否需要回滚（每次任务后都检查）
        rollback_result = self.check_and_rollback(agent_id)
        if rollback_result:
            rollback_executed = rollback_result

            # 发送回滚告警
            self.notifier.notify_rollback(
                agent_id=agent_id,
                reason=rollback_result.get("reason", "unknown"),
                metrics={
                    "before_metrics": rollback_result.get("before_metrics", {}),
                    "after_metrics": rollback_result.get("after_metrics", {})
                }
            )

        return {
            "success": success,
            "result": result,
            "error": error,
            "duration_sec": duration,
            "improvement_triggered": improvement_triggered,
            "improvement_applied": improvement_applied,
            "rollback_executed": rollback_executed
        }

    def track(
        self,
        agent_id: str,
        task: str,
        execute_fn: Callable[[], Any],
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Short alias for ``execute_with_improvement``."""
        return self.execute_with_improvement(
            agent_id=agent_id,
            task=task,
            execute_fn=execute_fn,
            context=context,
        )

    def _record_trace(self, agent_id: str, task: str, success: bool, 
                     duration: float, error: str = None, context: Dict = None):
        """记录任务追踪"""
        trace = {
            "agent_id": agent_id,
            "task": task,
            "success": success,
            "duration_sec": duration,
            "error": error,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }

        self.trace_store.append(trace)

    def _should_trigger_improvement(self, agent_id: str) -> bool:
        """判断是否应该触发改进循环（使用自适应阈值）"""
        # 获取任务历史
        traces = self._load_traces(agent_id)

        # 获取自适应阈值
        failure_threshold, analysis_window_hours, cooldown_hours = \
            self.adaptive_threshold.get_threshold(agent_id, traces)

        # 检查冷却期
        last_improvement = self.state.get("last_improvement", {}).get(agent_id)
        if last_improvement:
            last_time = datetime.fromisoformat(last_improvement)
            cooldown = timedelta(hours=cooldown_hours)
            if datetime.now() - last_time < cooldown:
                self._log("info", f"Agent {agent_id} 在冷却期内（{cooldown_hours}h），跳过改进")
                return False

        # 检查最近失败次数
        cutoff = datetime.now() - timedelta(hours=analysis_window_hours)
        recent_traces = [
            t for t in traces
            if (ts := parse_trace_timestamp(t)) is not None and ts > cutoff
        ]

        failures = [t for t in recent_traces if not t.get("success")]
        if len(failures) < failure_threshold:
            self._log("info", f"Agent {agent_id} 失败次数不足 ({len(failures)}/{failure_threshold})，跳过改进")
            return False

        self._log("info", f"Agent {agent_id} 触发改进（失败 {len(failures)}/{failure_threshold}，窗口 {analysis_window_hours}h）")
        return True

    def _run_improvement_cycle(self, agent_id: str) -> int:
        """Run the improvement cycle via the optional strategy hook."""
        self._log("info", f"触发 Agent {agent_id} 的改进循环")

        applied_count = 0
        if self.improvement_strategy is None:
            self._log("info", "未配置 improvement_strategy，仅记录触发，不伪装 strategy-apply")
        else:
            traces = self._load_traces(agent_id)
            before_metrics = self._calculate_metrics(agent_id)
            improvement_id = f"improvement_{int(time.time())}"

            try:
                config_patch = self.improvement_strategy.analyze(
                    agent_id=agent_id,
                    traces=traces,
                    before_metrics=before_metrics,
                )
            except Exception as e:
                self._log("error", f"improvement_strategy.analyze 失败: {e}")
                config_patch = None

            if config_patch:
                try:
                    current_config = self._get_current_config(agent_id)
                    backup_id = self.auto_rollback.backup_config(
                        agent_id=agent_id,
                        config=current_config,
                        improvement_id=improvement_id,
                    )

                    applied = self._apply_config_patch(agent_id, config_patch)
                    if applied is not False:
                        applied_count = 1
                        self.state.setdefault("backups", {})[agent_id] = {
                            "backup_id": backup_id,
                            "improvement_id": improvement_id,
                            "before_metrics": before_metrics,
                            "config_patch": config_patch,
                        }
                except Exception as e:
                    self._log("error", f"improvement_strategy.apply 失败: {e}")

        if "last_improvement" not in self.state:
            self.state["last_improvement"] = {}
        self.state["last_improvement"][agent_id] = datetime.now().isoformat()
        self._save_state()

        return applied_count

    def _get_current_config(self, agent_id: str) -> Dict[str, Any]:
        """Read the current config through the strongest available contract."""
        if self.config_adapter is not None:
            return dict(self.config_adapter.get_config(agent_id=agent_id))

        current_config_fn = getattr(self.improvement_strategy, "current_config", None)
        if current_config_fn is None:
            return {}
        return dict(current_config_fn(agent_id=agent_id))

    def _apply_config_patch(self, agent_id: str, config_patch: Dict[str, Any]) -> Any:
        """Apply a patch through ConfigAdapter, falling back to legacy strategy."""
        if self.config_adapter is not None:
            return self.config_adapter.apply_config(
                agent_id=agent_id,
                config_patch=config_patch,
            )

        apply_fn = getattr(self.improvement_strategy, "apply", None)
        if apply_fn is None:
            self._log("warn", "improvement_strategy 缺少 apply，无法应用 config_patch")
            return False
        return apply_fn(agent_id=agent_id, config_patch=config_patch)

    def _restore_config(self, agent_id: str, backup_config: Dict[str, Any]) -> Dict[str, Any]:
        """Restore a backed-up config; never silently claim success."""
        if self.config_adapter is not None:
            self.config_adapter.rollback_config(
                agent_id=agent_id,
                backup_config=backup_config,
            )
            return {"restore_applied": True, "restore_source": "config_adapter"}

        restore_fn = getattr(self.improvement_strategy, "rollback", None)
        if restore_fn is None:
            return {
                "restore_applied": False,
                "restore_source": "none",
                "error": "No config_adapter.rollback_config or improvement_strategy.rollback hook configured",
            }

        restore_fn(
            agent_id=agent_id,
            backup_config=backup_config,
        )
        return {"restore_applied": True, "restore_source": "improvement_strategy"}

    def check_and_rollback(self, agent_id: str) -> Optional[Dict]:
        """检查是否需要回滚，如果需要则执行"""
        # 检查是否有备份
        backup_info = self.state.get("backups", {}).get(agent_id)
        if not backup_info:
            return None

        # 计算改进后的指标
        after_metrics = self._calculate_metrics(agent_id)

        # 检查是否达到验证窗口
        if after_metrics["total_tasks"] < self.auto_rollback.VERIFICATION_WINDOW:
            return None

        # 判断是否需要回滚
        before_metrics = backup_info["before_metrics"]
        should_rollback, reason = self.auto_rollback.should_rollback(
            agent_id,
            backup_info["improvement_id"],
            before_metrics,
            after_metrics
        )

        if should_rollback:
            self._log("warn", f"检测到效果变差，执行回滚: {reason}")

            # 执行回滚
            result = self.auto_rollback.rollback(
                agent_id,
                backup_info["backup_id"]
            )

            if result["success"]:
                try:
                    restore_result = self._restore_config(
                        agent_id=agent_id,
                        backup_config=result.get("config", {}),
                    )
                except Exception as e:
                    self._log("error", f"config restore 失败: {e}")
                    return {
                        "agent_id": agent_id,
                        "reason": reason,
                        "before_metrics": before_metrics,
                        "after_metrics": after_metrics,
                        "backup_id": backup_info["backup_id"],
                        "success": False,
                        "restore_applied": False,
                        "error": str(e),
                    }

                if not restore_result.get("restore_applied"):
                    self._log("error", f"回滚判定已记录，但未执行真实配置恢复: {restore_result.get('error')}")
                    return {
                        "agent_id": agent_id,
                        "reason": reason,
                        "before_metrics": before_metrics,
                        "after_metrics": after_metrics,
                        "backup_id": backup_info["backup_id"],
                        "success": False,
                        **restore_result,
                    }

                self._log("success", f"回滚成功: {agent_id}")

                # 清除备份信息
                if "backups" in self.state and agent_id in self.state["backups"]:
                    del self.state["backups"][agent_id]
                self._save_state()

                return {
                    "agent_id": agent_id,
                    "reason": reason,
                    "before_metrics": before_metrics,
                    "after_metrics": after_metrics,
                    "backup_id": backup_info["backup_id"],
                    "success": True,
                    **restore_result,
                }

        return None

    def _calculate_metrics(self, agent_id: str) -> Dict:
        """计算 Agent 的当前指标"""
        traces = self._load_traces(agent_id)

        # 获取自适应窗口
        _, analysis_window_hours, _ = self.adaptive_threshold.get_threshold(agent_id, traces)

        cutoff = datetime.now() - timedelta(hours=analysis_window_hours)
        recent_traces = [
            t for t in traces
            if (ts := parse_trace_timestamp(t)) is not None and ts > cutoff
        ]

        if not recent_traces:
            return {
                "success_rate": 0.0,
                "avg_duration_sec": 0.0,
                "total_tasks": 0,
                "consecutive_failures": 0
            }

        total = len(recent_traces)
        successes = sum(1 for t in recent_traces if t.get("success"))
        success_rate = successes / total if total > 0 else 0.0

        total_duration = sum(t.get("duration_sec", 0) for t in recent_traces)
        avg_duration = total_duration / total if total > 0 else 0.0

        # 计算连续失败次数
        consecutive_failures = 0
        for trace in reversed(recent_traces):
            if not trace.get("success"):
                consecutive_failures += 1
            else:
                break

        return {
            "success_rate": success_rate,
            "avg_duration_sec": avg_duration,
            "total_tasks": total,
            "consecutive_failures": consecutive_failures
        }

    def _load_traces(self, agent_id: str = None) -> list:
        """加载追踪记录"""
        return self.trace_store.load(agent_id=agent_id)

    def get_improvement_stats(self, agent_id: str = None) -> Dict:
        """获取改进统计"""
        if agent_id:
            # 单个 Agent 的统计
            traces = self._load_traces(agent_id)
            last_improvement = self.state.get("last_improvement", {}).get(agent_id)
            rollback_history = self.auto_rollback.get_rollback_history(agent_id)

            return {
                "agent_id": agent_id,
                "total_tasks": len(traces),
                "last_improvement": last_improvement,
                "rollback_count": len(rollback_history),
                "rollback_history": rollback_history[-5:]
            }
        else:
            # 全局统计
            rollback_stats = self.auto_rollback.get_stats()

            return {
                "total_improvements": len(self.state.get("last_improvement", {})),
                "agents_improved": list(self.state.get("last_improvement", {}).keys()),
                "total_rollbacks": rollback_stats["total_rollbacks"],
                "agents_rolled_back": rollback_stats["agents_rolled_back"]
            }

    def _load_state(self) -> Dict:
        """加载状态文件"""
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_state(self):
        """保存状态文件"""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _log(self, level: str, message: str):
        """写日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
