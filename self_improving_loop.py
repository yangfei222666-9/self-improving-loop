"""
Self-Improving Loop - 统一的 Agent 自我改进闭环

这是所有 Agent 的中间件层，自动嵌入到每个任务执行流程中：

  ┌─────────────────────────────────────────────────────────┐
  │                  Self-Improving Loop                     │
  │                                                          │
  │  1. Execute Task    → 执行任务（透明代理）               │
  │  2. Record Result   → 记录结果（AgentTracer）            │
  │  3. Analyze Failure → 分析失败模式（FailureAnalyzer）    │
  │  4. Generate Fix    → 生成改进建议（AutoEvolution）      │
  │  5. Auto Apply      → 自动应用低风险改进（AutoFixer）    │
  │  6. Verify Effect   → 验证效果（A/B 测试）               │
  │  7. Update Config   → 更新 Agent 配置（AgentManager）    │
  │                                                          │
  └─────────────────────────────────────────────────────────┘

使用方式：
    from self_improving_loop import SelfImprovingLoop
    
    loop = SelfImprovingLoop()
    
    # 包装任务执行
    result = loop.execute_with_improvement(
        agent_id="coder-001",
        task="修复登录 bug",
        execute_fn=lambda: agent.run_task(task)
    )
"""

import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_tracer import AgentTracer, TraceAnalyzer
from analyze_failures import FailureAnalyzer
from agent_auto_fixer import AgentAutoFixer
from auto_evolution import AutoEvolution
from evolution_ab_test import EvolutionABTest
from auto_rollback import AutoRollback
from adaptive_threshold import AdaptiveThreshold
from telegram_notifier import TelegramNotifier  # 新增

# AgentManager 导入（尝试多种路径）
try:
    from core.agent_manager import AgentManager
except ImportError:
    try:
        from aios.agent_system.core.agent_manager import AgentManager
    except ImportError:
        # 如果都失败，创建一个简化版
        class AgentManager:
            def __init__(self, data_dir):
                self.agents = {}
            def get_agent(self, agent_id):
                return self.agents.get(agent_id)
            def update_stats(self, agent_id, success, duration):
                pass

AIOS_ROOT = Path(__file__).resolve().parent.parent
LOOP_STATE_FILE = AIOS_ROOT / "agent_system" / "data" / "loop_state.json"
LOOP_LOG_FILE = AIOS_ROOT / "agent_system" / "data" / "loop.log"


class SelfImprovingLoop:
    """统一的 Agent 自我改进闭环"""

    # 配置常量
    MIN_FAILURES_FOR_ANALYSIS = 3      # 最少失败次数才触发分析
    ANALYSIS_WINDOW_HOURS = 24         # 分析窗口（小时）
    IMPROVEMENT_COOLDOWN_HOURS = 6     # 改进冷却期（小时）
    AUTO_APPLY_RISK_LEVEL = "low"      # 自动应用的风险等级

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = AIOS_ROOT / "agent_system" / "data"
        self.data_dir = Path(data_dir)

        # 初始化子模块
        self.agent_manager = AgentManager(str(self.data_dir))
        self.failure_analyzer = FailureAnalyzer()
        self.auto_fixer = AgentAutoFixer(auto_apply=False)
        self.auto_evolution = AutoEvolution(str(self.data_dir))
        self.ab_test = EvolutionABTest()  # 不需要参数
        self.auto_rollback = AutoRollback()
        self.adaptive_threshold = AdaptiveThreshold()
        self.notifier = TelegramNotifier(enabled=True)  # 新增

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
                "improvement_applied": int
            }
        """
        # Step 1: 执行任务 + 记录追踪
        tracer = AgentTracer(agent_id)
        tracer.start_task(task, context)

        start_time = time.time()
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
            duration = time.time() - start_time

        # 更新 Agent 统计
        self.agent_manager.update_stats(agent_id, success, duration)

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
            "rollback_executed": rollback_executed  # 新增
        }

    def _should_trigger_improvement(self, agent_id: str) -> bool:
        """判断是否应该触发改进循环（使用自适应阈值）"""
        # 获取任务历史
        analyzer = TraceAnalyzer()
        agent_traces = [t for t in analyzer.traces if t["agent_id"] == agent_id]

        # 获取自适应阈值
        failure_threshold, analysis_window_hours, cooldown_hours = \
            self.adaptive_threshold.get_threshold(agent_id, agent_traces)

        # 检查冷却期（使用自适应冷却期）
        last_improvement = self.state.get("last_improvement", {}).get(agent_id)
        if last_improvement:
            last_time = datetime.fromisoformat(last_improvement)
            cooldown = timedelta(hours=cooldown_hours)
            if datetime.now() - last_time < cooldown:
                self._log("info", f"Agent {agent_id} 在冷却期内（{cooldown_hours}h），跳过改进")
                return False

        # 检查最近失败次数（使用自适应窗口和阈值）
        cutoff = datetime.now() - timedelta(hours=analysis_window_hours)
        recent_traces = [
            t for t in agent_traces
            if datetime.fromisoformat(t["start_time"]) > cutoff
        ]

        failures = [t for t in recent_traces if not t.get("success")]
        if len(failures) < failure_threshold:
            self._log("info", f"Agent {agent_id} 失败次数不足 ({len(failures)}/{failure_threshold})，跳过改进")
            return False

        self._log("info", f"Agent {agent_id} 触发改进（失败 {len(failures)}/{failure_threshold}，窗口 {analysis_window_hours}h）")
        return True

    def _run_improvement_cycle(self, agent_id: str) -> int:
        """
        运行完整的改进循环（带自动回滚）

        Returns:
            应用的改进数量
        """
        self._log("info", f"触发 Agent {agent_id} 的改进循环")

        applied_count = 0

        # Step 2.5: 记录改进前的基线指标
        before_metrics = self._calculate_metrics(agent_id)
        self._log("info", f"改进前指标: 成功率 {before_metrics.get('success_rate', 0):.1%}, 平均耗时 {before_metrics.get('avg_duration_sec', 0):.1f}s")

        # Step 3: 分析失败模式
        report = self.failure_analyzer.analyze(
            days=1,  # 只分析最近 24 小时
            min_occurrences=self.MIN_FAILURES_FOR_ANALYSIS
        )

        # 筛选出该 Agent 的改进建议
        agent_improvements = [
            imp for imp in report.get("improvements", [])
            if imp.get("agent_id") == agent_id or
               (isinstance(imp.get("affected_agents"), list) and agent_id in imp.get("affected_agents", []))
        ]

        if not agent_improvements:
            self._log("info", f"Agent {agent_id} 无改进建议")
            return 0

        self._log("info", f"Agent {agent_id} 发现 {len(agent_improvements)} 条改进建议")

        # Step 4: 备份当前配置
        agent = self.agent_manager.get_agent(agent_id)
        if agent:
            improvement_id = f"improvement_{int(time.time())}"
            backup_id = self.auto_rollback.backup_config(
                agent_id, agent, improvement_id
            )
            self._log("info", f"已备份配置: {backup_id}")

            # 记录备份信息到状态
            if "backups" not in self.state:
                self.state["backups"] = {}
            self.state["backups"][agent_id] = {
                "backup_id": backup_id,
                "improvement_id": improvement_id,
                "before_metrics": before_metrics,
                "timestamp": datetime.now().isoformat()
            }
            self._save_state()

        # Step 5: 生成并应用改进
        for improvement in agent_improvements:
            risk = improvement.get("risk", "high")

            # 只自动应用低风险改进
            if risk != self.AUTO_APPLY_RISK_LEVEL:
                self._log("info", f"跳过 {risk} 风险改进: {improvement['description']}")
                continue

            # 应用改进
            fix_result = self.auto_fixer._apply_fix(improvement)
            if fix_result.get("success"):
                applied_count += 1
                self._log("success", f"应用改进: {improvement['description']}")

                # Step 6: 启动 A/B 测试验证
                self._start_ab_test(agent_id, improvement)
            else:
                self._log("error", f"应用改进失败: {fix_result.get('error')}")

        # Step 7: 尝试 Prompt 进化
        evolution_result = self.auto_evolution.auto_evolve(agent_id, self.agent_manager)
        if evolution_result.get("status") == "applied":
            applied_count += len(evolution_result.get("plans", []))
            self._log("success", f"应用 Prompt 进化: {len(evolution_result.get('plans', []))} 项")

        # 更新状态
        if "last_improvement" not in self.state:
            self.state["last_improvement"] = {}
        self.state["last_improvement"][agent_id] = datetime.now().isoformat()
        self._save_state()

        return applied_count

    def _start_ab_test(self, agent_id: str, improvement: Dict):
        """启动 A/B 测试验证改进效果（简化版，仅记录）"""
        test_id = f"{agent_id}_{int(time.time())}"
        self._log("info", f"标记 A/B 测试: {test_id} - {improvement['description']}")

    def _calculate_metrics(self, agent_id: str) -> Dict:
        """
        计算 Agent 的当前指标（使用自适应窗口）

        Returns:
            {
                "success_rate": float,
                "avg_duration_sec": float,
                "total_tasks": int,
                "consecutive_failures": int
            }
        """
        analyzer = TraceAnalyzer()
        agent_traces = [t for t in analyzer.traces if t["agent_id"] == agent_id]

        # 获取自适应窗口
        _, analysis_window_hours, _ = self.adaptive_threshold.get_threshold(agent_id, agent_traces)
        
        cutoff = datetime.now() - timedelta(hours=analysis_window_hours)
        
        recent_traces = [
            t for t in agent_traces
            if datetime.fromisoformat(t["start_time"]) > cutoff
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

    def check_and_rollback(self, agent_id: str) -> Optional[Dict]:
        """
        检查是否需要回滚，如果需要则执行

        Returns:
            回滚结果（如果执行了回滚）
        """
        # 检查是否有备份
        backup_info = self.state.get("backups", {}).get(agent_id)
        if not backup_info:
            return None

        # 计算改进后的指标
        after_metrics = self._calculate_metrics(agent_id)

        # 检查是否达到验证窗口
        if after_metrics["total_tasks"] < self.auto_rollback.VERIFICATION_WINDOW:
            # 还没有足够的数据
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
                    "backup_id": backup_info["backup_id"]
                }
            else:
                self._log("error", f"回滚失败: {result.get('error')}")

        else:
            # 效果良好，确认改进成功
            self._log("info", f"改进效果良好，确认成功: {agent_id}")

            # 清除备份信息
            if "backups" in self.state and agent_id in self.state["backups"]:
                del self.state["backups"][agent_id]
            self._save_state()

        return None

    def get_improvement_stats(self, agent_id: str = None) -> Dict:
        """获取改进统计"""
        if agent_id:
            # 单个 Agent 的统计
            agent = self.agent_manager.get_agent(agent_id)
            if not agent:
                return {"error": "Agent not found"}

            last_improvement = self.state.get("last_improvement", {}).get(agent_id)
            return {
                "agent_id": agent_id,
                "agent_stats": agent.get("stats", {}),  # 改为 agent_stats
                "last_improvement": last_improvement,
                "cooldown_remaining_hours": self._get_cooldown_remaining(agent_id)
            }
        else:
            # 全局统计
            total_improvements = sum(
                1 for _ in self.state.get("last_improvement", {}).values()
            )
            return {
                "total_agents": len(self.agent_manager.agents),
                "total_improvements": total_improvements,
                "agents_improved": list(self.state.get("last_improvement", {}).keys())
            }

    def _get_cooldown_remaining(self, agent_id: str) -> float:
        """获取剩余冷却时间（小时）"""
        last_improvement = self.state.get("last_improvement", {}).get(agent_id)
        if not last_improvement:
            return 0.0

        last_time = datetime.fromisoformat(last_improvement)
        cooldown = timedelta(hours=self.IMPROVEMENT_COOLDOWN_HOURS)
        elapsed = datetime.now() - last_time
        remaining = cooldown - elapsed

        return max(0, remaining.total_seconds() / 3600)

    def _load_state(self) -> Dict:
        """加载状态文件"""
        if LOOP_STATE_FILE.exists():
            with open(LOOP_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_state(self):
        """保存状态文件"""
        LOOP_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOOP_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _log(self, level: str, message: str):
        """写日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        LOOP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOOP_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================================
# 使用示例
# ============================================================================

def example_usage():
    """使用示例"""
    loop = SelfImprovingLoop()

    # 模拟任务执行
    def mock_task():
        # 模拟一个会失败的任务
        import random
        if random.random() < 0.3:  # 30% 失败率
            raise Exception("模拟错误：网络超时")
        return {"status": "success", "data": "任务完成"}

    # 执行任务（自动嵌入改进循环）
    result = loop.execute_with_improvement(
        agent_id="coder-001",
        task="修复登录 bug",
        execute_fn=mock_task,
        context={"file": "auth.py", "line": 42}
    )

    print(f"任务结果: {result['success']}")
    print(f"改进触发: {result['improvement_triggered']}")
    print(f"改进应用: {result['improvement_applied']}")

    # 查看统计
    stats = loop.get_improvement_stats("coder-001")
    print(f"\nAgent 统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    example_usage()
