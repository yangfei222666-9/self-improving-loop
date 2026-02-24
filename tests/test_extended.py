"""
Self-Improving Loop 扩展测试套件

测试边界情况、错误处理、并发场景等。
"""

import sys
import json
import time
import tempfile
import shutil
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

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
    def __init__(self):
        self.path = Path(tempfile.mkdtemp(prefix="sil_test_"))

    def cleanup(self):
        shutil.rmtree(self.path, ignore_errors=True)


def test_edge_cases():
    """测试边界情况"""
    print("Test 1: 边界情况")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        # 空任务
        result = loop.execute_with_improvement(
            agent_id="edge-001",
            task="",
            execute_fn=lambda: None
        )
        assert result["success"] is True
        print("  ✓ 空任务处理正常")

        # 超长任务名
        long_task = "x" * 10000
        result = loop.execute_with_improvement(
            agent_id="edge-001",
            task=long_task,
            execute_fn=lambda: {"ok": True}
        )
        assert result["success"] is True
        print("  ✓ 超长任务名处理正常")

        # None 返回值
        result = loop.execute_with_improvement(
            agent_id="edge-001",
            task="返回 None",
            execute_fn=lambda: None
        )
        assert result["success"] is True
        assert result["result"] is None
        print("  ✓ None 返回值处理正常")

    finally:
        tmp.cleanup()


def test_error_handling():
    """测试错误处理"""
    print("\nTest 2: 错误处理")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        # 各种异常类型
        exceptions = [
            ValueError("值错误"),
            TypeError("类型错误"),
            RuntimeError("运行时错误"),
            KeyError("键错误"),
            IndexError("索引错误"),
        ]

        for exc in exceptions:
            result = loop.execute_with_improvement(
                agent_id="error-001",
                task=f"触发 {type(exc).__name__}",
                execute_fn=lambda e=exc: (_ for _ in ()).throw(e)
            )
            assert result["success"] is False
            assert result["error"] is not None
            print(f"  ✓ {type(exc).__name__} 处理正常")

        # 嵌套异常
        def nested_error():
            def inner():
                raise ValueError("内部错误")
            try:
                inner()
            except ValueError as e:
                raise RuntimeError("外部错误") from e

        result = loop.execute_with_improvement(
            agent_id="error-001",
            task="嵌套异常",
            execute_fn=nested_error
        )
        assert result["success"] is False
        print("  ✓ 嵌套异常处理正常")

    finally:
        tmp.cleanup()


def test_concurrent_execution():
    """测试并发执行"""
    print("\nTest 3: 并发执行")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        def worker(i):
            return loop.execute_with_improvement(
                agent_id=f"worker-{i % 3}",  # 3 个 Agent
                task=f"任务 {i}",
                execute_fn=lambda: {"id": i, "result": i * 2}
            )

        # 10 个线程并发执行 100 个任务
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(worker, range(100)))

        # 验证结果
        assert len(results) == 100
        assert all(r["success"] for r in results)
        print(f"  ✓ 100 个并发任务全部成功")

        # 验证追踪数据
        analyzer = TraceAnalyzer(tmp.path / "traces")
        assert len(analyzer.traces) == 100
        print(f"  ✓ 追踪数据完整（{len(analyzer.traces)} 条）")

    finally:
        tmp.cleanup()


def test_large_dataset():
    """测试大数据量"""
    print("\nTest 4: 大数据量")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        # 执行 1000 个任务
        for i in range(1000):
            loop.execute_with_improvement(
                agent_id="bulk-agent",
                task=f"任务 {i}",
                execute_fn=lambda i=i: {"id": i}
            )

        # 验证统计
        stats = loop.get_improvement_stats("bulk-agent")
        assert stats["agent_stats"]["tasks_completed"] == 1000
        print("  ✓ 1000 个任务执行完成")

        # 验证追踪文件大小
        trace_file = tmp.path / "traces" / "agent_traces.jsonl"
        size_mb = trace_file.stat().st_size / 1024 / 1024
        print(f"  ✓ 追踪文件大小: {size_mb:.2f} MB")

    finally:
        tmp.cleanup()


def test_rollback_scenarios():
    """测试回滚场景"""
    print("\nTest 5: 回滚场景")
    tmp = TempDir()
    try:
        rollback = AutoRollback(tmp.path / "rollback")

        # 场景 1: 成功率下降触发回滚
        before = {"success_rate": 0.90, "avg_duration_sec": 5.0}
        after = {"success_rate": 0.75, "avg_duration_sec": 5.0}
        should, reason = rollback.should_rollback("agent-1", "imp-1", before, after)
        assert should is True
        assert "成功率下降" in reason
        print("  ✓ 成功率下降触发回滚")

        # 场景 2: 耗时增加触发回滚
        before = {"success_rate": 0.80, "avg_duration_sec": 10.0}
        after = {"success_rate": 0.80, "avg_duration_sec": 15.0}
        should, reason = rollback.should_rollback("agent-2", "imp-2", before, after)
        assert should is True
        assert "耗时增加" in reason
        print("  ✓ 耗时增加触发回滚")

        # 场景 3: 连续失败触发回滚
        before = {"success_rate": 0.80}
        after = {"success_rate": 0.80, "consecutive_failures": 5}
        should, reason = rollback.should_rollback("agent-3", "imp-3", before, after)
        assert should is True
        assert "连续失败" in reason
        print("  ✓ 连续失败触发回滚")

        # 场景 4: 轻微下降不触发回滚
        before = {"success_rate": 0.80, "avg_duration_sec": 10.0}
        after = {"success_rate": 0.78, "avg_duration_sec": 10.5}
        should, _ = rollback.should_rollback("agent-4", "imp-4", before, after)
        assert should is False
        print("  ✓ 轻微下降不触发回滚")

    finally:
        tmp.cleanup()


def test_threshold_adaptation():
    """测试阈值自适应"""
    print("\nTest 6: 阈值自适应")
    tmp = TempDir()
    try:
        at = AdaptiveThreshold(tmp.path / "thresholds.json")

        # 高频 Agent
        from datetime import datetime, timedelta
        now = datetime.now()
        high_freq_history = [
            {"start_time": (now - timedelta(hours=i)).isoformat()}
            for i in range(15)
        ]
        t, w, c = at.get_threshold("high-freq", high_freq_history)
        assert t == 5 and w == 48 and c == 3
        print("  ✓ 高频 Agent 阈值正确 (5, 48h, 3h)")

        # 低频 Agent
        low_freq_history = [
            {"start_time": (now - timedelta(hours=i*12)).isoformat()}
            for i in range(2)
        ]
        t, w, c = at.get_threshold("low-freq", low_freq_history)
        assert t == 2 and w == 72 and c == 12
        print("  ✓ 低频 Agent 阈值正确 (2, 72h, 12h)")

        # 关键 Agent
        t, w, c = at.get_threshold("prod-monitor", [])
        assert t == 1
        print("  ✓ 关键 Agent 阈值正确 (1)")

        # 手动配置优先级
        at.set_manual_threshold("custom", failure_threshold=99)
        t, _, _ = at.get_threshold("custom", [])
        assert t == 99
        print("  ✓ 手动配置优先级正确")

    finally:
        tmp.cleanup()


def test_memory_efficiency():
    """测试内存效率"""
    print("\nTest 7: 内存效率")
    tmp = TempDir()
    try:
        import tracemalloc
        tracemalloc.start()

        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        # 执行 100 个任务
        for i in range(100):
            loop.execute_with_improvement(
                agent_id="mem-test",
                task=f"任务 {i}",
                execute_fn=lambda: {"data": "x" * 1000}
            )

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"  ✓ 当前内存: {current / 1024 / 1024:.2f} MB")
        print(f"  ✓ 峰值内存: {peak / 1024 / 1024:.2f} MB")

        # 验证内存不会无限增长
        assert peak < 50 * 1024 * 1024  # < 50 MB

    finally:
        tmp.cleanup()


def test_data_persistence():
    """测试数据持久化"""
    print("\nTest 8: 数据持久化")
    tmp = TempDir()
    try:
        # 第一个循环：写入数据
        loop1 = SelfImprovingLoop(data_dir=str(tmp.path))
        for i in range(10):
            loop1.execute_with_improvement(
                agent_id="persist-agent",
                task=f"任务 {i}",
                execute_fn=lambda: {"ok": True}
            )

        # 第二个循环：读取数据
        loop2 = SelfImprovingLoop(data_dir=str(tmp.path))
        stats = loop2.get_improvement_stats("persist-agent")
        assert stats["agent_stats"]["tasks_completed"] == 10
        print("  ✓ 数据持久化正常")

        # 验证追踪数据
        analyzer = TraceAnalyzer(tmp.path / "traces")
        assert len(analyzer.traces) == 10
        print("  ✓ 追踪数据持久化正常")

    finally:
        tmp.cleanup()


def test_notifier_integration():
    """测试通知器集成"""
    print("\nTest 9: 通知器集成")
    tmp = TempDir()
    try:
        from self_improving_loop.notifier import Notifier

        # 自定义通知器
        notifications = []

        class TestNotifier(Notifier):
            def notify_improvement(self, agent_id, count, details=None):
                notifications.append(("improvement", agent_id, count))

            def notify_rollback(self, agent_id, reason, metrics=None):
                notifications.append(("rollback", agent_id, reason))

        notifier = TestNotifier()
        loop = SelfImprovingLoop(data_dir=str(tmp.path), notifier=notifier)

        # 触发改进（需要多次失败）
        for i in range(5):
            loop.execute_with_improvement(
                agent_id="notify-test",
                task=f"失败 {i}",
                execute_fn=lambda: 1 / 0
            )

        # 验证通知
        assert len(notifications) > 0
        print(f"  ✓ 收到 {len(notifications)} 条通知")

    finally:
        tmp.cleanup()


def test_performance_benchmark():
    """测试性能基准"""
    print("\nTest 10: 性能基准")
    tmp = TempDir()
    try:
        loop = SelfImprovingLoop(data_dir=str(tmp.path))

        # 测试单次执行耗时
        start = time.time()
        loop.execute_with_improvement(
            agent_id="perf-test",
            task="性能测试",
            execute_fn=lambda: {"ok": True}
        )
        single_duration = time.time() - start
        print(f"  ✓ 单次执行耗时: {single_duration*1000:.2f}ms")

        # 测试批量执行耗时
        start = time.time()
        for i in range(100):
            loop.execute_with_improvement(
                agent_id="perf-test",
                task=f"任务 {i}",
                execute_fn=lambda: {"ok": True}
            )
        batch_duration = time.time() - start
        avg_duration = batch_duration / 100
        print(f"  ✓ 批量执行平均耗时: {avg_duration*1000:.2f}ms")

        # 验证性能合理
        assert avg_duration < 0.1  # < 100ms per task

    finally:
        tmp.cleanup()


def run_all():
    print("=" * 60)
    print("  Self-Improving Loop 扩展测试套件")
    print("=" * 60)

    tests = [
        test_edge_cases,
        test_error_handling,
        test_concurrent_execution,
        test_large_dataset,
        test_rollback_scenarios,
        test_threshold_adaptation,
        test_memory_efficiency,
        test_data_persistence,
        test_notifier_integration,
        test_performance_benchmark,
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
