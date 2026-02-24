"""
Self-Improving Loop 使用示例

展示如何将 Self-Improving Loop 集成到你的 Agent 系统中。

安装后直接 import：
    pip install self-improving-loop
    from self_improving_loop import SelfImprovingLoop

开发模式运行：
    python -m examples.basic_usage
"""

import sys
from pathlib import Path

# 开发模式：添加 src 到路径（安装后不需要）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from self_improving_loop import SelfImprovingLoop, PrintNotifier


def example_basic():
    """基础用法：包装任务执行"""
    print("=== 基础用法 ===\n")

    loop = SelfImprovingLoop(data_dir="./example_data")

    # 成功任务
    result = loop.execute_with_improvement(
        agent_id="coder-001",
        task="修复登录 bug",
        execute_fn=lambda: {"status": "fixed", "lines_changed": 3},
    )
    print(f"成功: {result['success']}, 耗时: {result['duration_sec']:.2f}s")

    # 失败任务
    result = loop.execute_with_improvement(
        agent_id="coder-001",
        task="部署到生产环境",
        execute_fn=lambda: (_ for _ in ()).throw(Exception("网络超时")),
    )
    print(f"成功: {result['success']}, 错误: {result['error']}")
    print(f"改进触发: {result['improvement_triggered']}")


def example_custom_notifier():
    """自定义通知器"""
    print("\n=== 自定义通知器 ===\n")

    from self_improving_loop.notifier import Notifier

    class SlackNotifier(Notifier):
        def notify_improvement(self, agent_id, count, details=None):
            print(f"[Slack] Agent {agent_id} 改进了 {count} 项")

        def notify_rollback(self, agent_id, reason, metrics=None):
            print(f"[Slack] ⚠️ Agent {agent_id} 回滚: {reason}")

    loop = SelfImprovingLoop(
        data_dir="./example_data",
        notifier=SlackNotifier(),
    )

    result = loop.execute_with_improvement(
        agent_id="analyst-001",
        task="分析数据",
        execute_fn=lambda: {"insights": 5},
    )
    print(f"结果: {result['success']}")


def example_agent_class():
    """集成到 Agent 类"""
    print("\n=== Agent 类集成 ===\n")

    loop = SelfImprovingLoop(data_dir="./example_data")

    class MyAgent:
        def __init__(self, agent_id):
            self.agent_id = agent_id

        def run(self, task):
            return loop.execute_with_improvement(
                agent_id=self.agent_id,
                task=task,
                execute_fn=lambda: self._execute(task),
                context={"source": "example"},
            )

        def _execute(self, task):
            if "error" in task:
                raise RuntimeError(f"执行失败: {task}")
            return {"done": True}

    agent = MyAgent("worker-001")

    for task in ["正常任务", "error 任务", "另一个正常任务"]:
        result = agent.run(task)
        status = "✓" if result["success"] else "✗"
        print(f"  {status} {task}: {result.get('error', 'ok')}")

    # 查看统计
    stats = loop.get_improvement_stats("worker-001")
    print(f"\n统计: {stats['agent_stats']}")


def example_threshold_config():
    """自适应阈值配置"""
    print("\n=== 自适应阈值 ===\n")

    from self_improving_loop import AdaptiveThreshold

    at = AdaptiveThreshold()

    # 默认阈值
    t, w, c = at.get_threshold("normal-agent", [])
    print(f"普通 Agent: 阈值={t}, 窗口={w}h, 冷却={c}h")

    # 关键 Agent（名称包含 critical/monitor/prod）
    t, w, c = at.get_threshold("prod-monitor", [])
    print(f"关键 Agent: 阈值={t}, 窗口={w}h, 冷却={c}h")

    # 手动配置
    at.set_manual_threshold("special-agent", failure_threshold=10, cooldown_hours=1)
    t, w, c = at.get_threshold("special-agent", [])
    print(f"自定义 Agent: 阈值={t}, 窗口={w}h, 冷却={c}h")


if __name__ == "__main__":
    example_basic()
    example_custom_notifier()
    example_agent_class()
    example_threshold_config()

    # 清理示例数据
    import shutil
    shutil.rmtree("./example_data", ignore_errors=True)
    print("\n✓ 示例运行完成，已清理临时数据")
