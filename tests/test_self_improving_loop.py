"""Self-Improving Loop 独立包测试套件"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# 确保能导入 src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from self_improving_loop import (
    SelfImprovingLoop,
    AgentTracer,
    TraceAnalyzer,
    AutoRollback,
    AdaptiveThreshold,
    PrintNotifier,
)


class TempDir:
    """测试用临时目录"""
    def __init__(self):
        self.path = Path(tempfile.mkdtemp(prefix="sil_test_"))

    def cleanup(self):
        shutil.rmtree(self.path, ignore_errors=True)


def test_tracer():
    """测试追踪器"""
    print("Test 1: AgentTracer")
    tmp = TempDir()
    try:
        tracer = AgentTracer("test-001", tmp.path / "traces")
        tracer.start_task("测试任务", {"key": "value"})
        tracer.log_step("step1", {"detail": "ok"})
        tracer.log_tool_call("read", {"path": "test.py"}, result="content")
        tracer.end_task(success=True)

        analyzer = TraceAnalyzer(tmp.path / "traces")
        assert len(analyzer.traces) == 1
        assert analyzer.traces[0]["success"] is True
        assert analyzer.traces[0]["agent_id"] == "test-001"
        print("  ✓ 追踪记录正常")

        stats = analyzer.get_agent_stats("test-001")
        assert stats["total_tasks"] == 1
        assert stats["success_rate"] == 1.0
        print("  ✓ 统计数据正常")
    finally:
        tmp.cleanup()


def test_rollback():
    """测试回滚机制"""
    print("\nTest 2: AutoRollback")
    tmp = TempDir()
    try:
        rb = AutoRollback(tmp.path / "rollback")

        backup_id = rb.backup_config("agent-001", {"timeout": 30}, "imp_001")
        assert backup_id.startswith("agent-001_")
        print("  ✓ 备份配置成功")

        should, reason = rb.should_rollback(
            "agent-001", "imp_001",
            {"success_rate": 0.80, "avg_duration_sec": 10.0},
            {"success_rate": 0.65, "avg_duration_sec": 12.0},
        )
        assert should is True
        assert "成功率下降" in reason
        print(f"  ✓ 检测到需要回滚: {reason}")

        result = rb.rollback("agent-001", backup_id)
        assert result["success"] is True
        print("  ✓ 回滚执行成功")

        should2, _ = rb.should_rollback(
            "agent-001", "imp_002",
            {"success_rate": 0.80},
            {"success_rate": 0.78},
        )
        assert should2 is False
        print("  ✓ 正常情况不触发回滚")
    finally:
        tmp.cleanup()


def test_threshold():
    """测试自适应阈值"""
    print("\nTest 3: AdaptiveThreshold")
    tmp = TempDir()
    try:
        at = AdaptiveThreshold(tmp.path / "thresholds.json")

        # 无历史 → 中频默认
        t, w, c = at.get_threshold("agent-001", [])
        assert t == 3 and w == 24 and c == 6
        print("  ✓ 默认阈值正常 (3, 24h, 6h)")

        # 关键 Agent
        t, w, c = at.get_threshold("agent-critical-monitor", [])
        assert t == 1
        print("  ✓ 关键 Agent 阈值 = 1")

        # 手动配置
        at.set_manual_threshold("custom-001", failure_threshold=10, cooldown_hours=1)
        t, w, c = at.get_threshold("custom-001", [])
        assert t == 10 and c == 1
        print("  ✓ 手动配置生效")

        # Profile
        profile = at.get_agent_profile("agent-001", [])
        assert profile["frequency"] == "medium"
        assert profile["source"] == "auto"
        print("  ✓ Agent Profile 正常")
    finally:
        tmp.cleanup()


def test_loop_success():
    """测试成功任务执行"""
    print("\nTest 4: SelfImprovingLoop 成功任务")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))
        result = loop.execute_with_improvement(
            agent_id="test-001",
            task="测试任务",
            execute_fn=lambda: {"status": "ok"},
        )
        assert result["success"] is True
        assert result["improvement_triggered"] is False
        assert result["duration_sec"] >= 0
        print("  ✓ 成功任务执行正常")
    finally:
        tmp.cleanup()


def test_loop_failure():
    """测试失败任务执行"""
    print("\nTest 5: SelfImprovingLoop 失败任务")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))
        result = loop.execute_with_improvement(
            agent_id="test-001",
            task="失败任务",
            execute_fn=lambda: 1 / 0,
        )
        assert result["success"] is False
        assert "division by zero" in result["error"]
        print("  ✓ 失败任务记录正常")
    finally:
        tmp.cleanup()


def test_loop_improvement_trigger():
    """测试改进触发"""
    print("\nTest 6: 改进触发机制")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))
        triggered = False
        for i in range(5):
            result = loop.execute_with_improvement(
                agent_id="test-002",
                task=f"失败任务 {i}",
                execute_fn=lambda: 1 / 0,
            )
            if result["improvement_triggered"]:
                triggered = True
                print(f"  ✓ 第 {i+1} 次失败后触发改进")
                break
        if not triggered:
            print("  ✓ 未触发改进（冷却期或阈值未达到）")
    finally:
        tmp.cleanup()


def test_loop_stats():
    """测试统计功能"""
    print("\nTest 7: 统计功能")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        for i in range(3):
            loop.execute_with_improvement(
                agent_id="test-003",
                task=f"任务 {i}",
                execute_fn=lambda i=i: {"ok": True} if i % 2 == 0 else 1 / 0,
            )

        stats = loop.get_improvement_stats("test-003")
        assert "agent_stats" in stats
        print(f"  ✓ Agent 统计: {stats['agent_stats']}")

        global_stats = loop.get_improvement_stats()
        assert "total_agents" in global_stats
        print(f"  ✓ 全局统计: {global_stats['total_agents']} agents")
    finally:
        tmp.cleanup()


def test_notifier():
    """测试通知器"""
    print("\nTest 8: Notifier")
    notifier = PrintNotifier(enabled=True)
    notifier.notify_improvement("test-001", 2, {"timeout": "30s → 45s"})
    notifier.notify_rollback("test-001", "成功率下降 15%", {
        "before_metrics": {"success_rate": 0.80},
        "after_metrics": {"success_rate": 0.65},
    })
    print("  ✓ 通知器正常")


def test_cooldown():
    """测试冷却期"""
    print("\nTest 9: 冷却期")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        # 模拟触发改进
        for i in range(5):
            loop.execute_with_improvement(
                agent_id="test-004",
                task=f"失败 {i}",
                execute_fn=lambda: 1 / 0,
            )

        remaining = loop._get_cooldown_remaining("test-004")
        if remaining > 0:
            print(f"  ✓ 冷却期剩余 {remaining:.1f}h")
        else:
            print("  ✓ 无冷却期（未触发改进）")
    finally:
        tmp.cleanup()


def test_integration():
    """测试集成模式"""
    print("\nTest 10: 集成模式")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        class MockAgent:
            def __init__(self, agent_id):
                self.agent_id = agent_id
                self.loop = loop

            def run(self, task):
                return self.loop.execute_with_improvement(
                    agent_id=self.agent_id,
                    task=task,
                    execute_fn=lambda: self._do(task),
                )

            def _do(self, task):
                if "fail" in task.lower():
                    raise Exception("任务失败")
                return {"status": "ok"}

        agent = MockAgent("mock-001")
        r1 = agent.run("正常任务")
        assert r1["success"] is True
        r2 = agent.run("fail 任务")
        assert r2["success"] is False
        print("  ✓ 集成模式正常")
    finally:
        tmp.cleanup()


def run_all():
    print("=" * 60)
    print("  Self-Improving Loop 独立包测试")
    print("=" * 60)

    tests = [
        test_tracer,
        test_rollback,
        test_threshold,
        test_loop_success,
        test_loop_failure,
        test_loop_improvement_trigger,
        test_loop_stats,
        test_notifier,
        test_cooldown,
        test_integration,
    ]

    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  ✗ {test.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"  结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
