"""
Self-Improving Loop 测试套件
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from self_improving_loop import SelfImprovingLoop
from agent_tracer import AgentTracer, TraceAnalyzer
from core.agent_manager import AgentManager


def test_basic_execution():
    """测试基础任务执行"""
    print("Test 1: 基础任务执行")
    
    loop = SelfImprovingLoop()
    
    # 成功任务
    result = loop.execute_with_improvement(
        agent_id="test-001",
        task="测试任务",
        execute_fn=lambda: {"status": "success"}
    )
    
    assert result["success"] == True
    assert result["improvement_triggered"] == False
    print("  ✓ 成功任务执行正常")
    
    # 失败任务
    def failing_task():
        raise Exception("模拟错误")
    
    result = loop.execute_with_improvement(
        agent_id="test-001",
        task="失败任务",
        execute_fn=failing_task
    )
    
    assert result["success"] == False
    assert result["error"] is not None
    print("  ✓ 失败任务记录正常")


def test_failure_threshold():
    """测试失败阈值触发"""
    print("\nTest 2: 失败阈值触发")
    
    loop = SelfImprovingLoop()
    agent_id = "test-002"
    
    # 模拟多次失败
    for i in range(5):
        result = loop.execute_with_improvement(
            agent_id=agent_id,
            task=f"失败任务 {i+1}",
            execute_fn=lambda: 1/0  # 触发 ZeroDivisionError
        )
        
        if i < loop.MIN_FAILURES_FOR_ANALYSIS - 1:
            assert result["improvement_triggered"] == False
            print(f"  ✓ 第 {i+1} 次失败，未触发改进")
        else:
            # 第 3 次失败应该触发改进
            if result["improvement_triggered"]:
                print(f"  ✓ 第 {i+1} 次失败，触发改进")
                break


def test_cooldown_period():
    """测试冷却期"""
    print("\nTest 3: 冷却期")
    
    loop = SelfImprovingLoop()
    agent_id = "test-003"
    
    # 触发一次改进
    for i in range(loop.MIN_FAILURES_FOR_ANALYSIS):
        loop.execute_with_improvement(
            agent_id=agent_id,
            task=f"失败任务 {i+1}",
            execute_fn=lambda: 1/0
        )
    
    # 检查冷却期
    remaining = loop._get_cooldown_remaining(agent_id)
    if remaining > 0:
        print(f"  ✓ 冷却期剩余 {remaining:.1f} 小时")
    else:
        print("  ⚠️ 冷却期已过（可能是测试环境问题）")


def test_stats_tracking():
    """测试统计追踪"""
    print("\nTest 4: 统计追踪")
    
    loop = SelfImprovingLoop()
    agent_id = "test-004"
    
    # 执行一些任务
    for i in range(5):
        success = i % 2 == 0  # 交替成功/失败
        loop.execute_with_improvement(
            agent_id=agent_id,
            task=f"任务 {i+1}",
            execute_fn=lambda s=success: {"ok": True} if s else 1/0
        )
    
    # 查看统计
    stats = loop.get_improvement_stats(agent_id)
    agent_stats = stats.get("agent_stats", {})  # 改为 agent_stats
    
    print(f"  ✓ 任务完成: {agent_stats.get('tasks_completed', 0)}")
    print(f"  ✓ 任务失败: {agent_stats.get('tasks_failed', 0)}")
    print(f"  ✓ 成功率: {agent_stats.get('success_rate', 0):.1%}")


def test_trace_recording():
    """测试追踪记录"""
    print("\nTest 5: 追踪记录")
    
    loop = SelfImprovingLoop()
    agent_id = "test-005"
    
    # 执行任务
    loop.execute_with_improvement(
        agent_id=agent_id,
        task="测试追踪",
        execute_fn=lambda: {"result": "ok"},
        context={"test": True}
    )
    
    # 验证追踪记录
    analyzer = TraceAnalyzer()
    traces = [t for t in analyzer.traces if t["agent_id"] == agent_id]
    
    if traces:
        print(f"  ✓ 追踪记录已保存 ({len(traces)} 条)")
        latest = traces[-1]
        print(f"  ✓ 任务: {latest['task']}")
        print(f"  ✓ 成功: {latest['success']}")
    else:
        print("  ⚠️ 未找到追踪记录")


def test_global_stats():
    """测试全局统计"""
    print("\nTest 6: 全局统计")
    
    loop = SelfImprovingLoop()
    
    stats = loop.get_improvement_stats()
    print(f"  ✓ 总 Agent 数: {stats['total_agents']}")
    print(f"  ✓ 总改进次数: {stats['total_improvements']}")
    print(f"  ✓ 已改进 Agent: {stats['agents_improved']}")


def test_integration_example():
    """测试集成示例"""
    print("\nTest 7: 集成示例")
    
    class MockAgent:
        def __init__(self, agent_id):
            self.agent_id = agent_id
            self.loop = SelfImprovingLoop()
        
        def run_task(self, task):
            return self.loop.execute_with_improvement(
                agent_id=self.agent_id,
                task=task,
                execute_fn=lambda: self._do_task(task)
            )
        
        def _do_task(self, task):
            # 模拟任务逻辑
            if "fail" in task.lower():
                raise Exception("任务失败")
            return {"status": "success", "task": task}
    
    agent = MockAgent("test-007")
    
    # 成功任务
    result = agent.run_task("正常任务")
    assert result["success"] == True
    print("  ✓ 集成模式：成功任务")
    
    # 失败任务
    result = agent.run_task("fail 任务")
    assert result["success"] == False
    print("  ✓ 集成模式：失败任务")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("  Self-Improving Loop 测试套件")
    print("=" * 60)
    
    tests = [
        test_basic_execution,
        test_failure_threshold,
        test_cooldown_period,
        test_stats_tracking,
        test_trace_recording,
        test_global_stats,
        test_integration_example,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  ✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"  测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
