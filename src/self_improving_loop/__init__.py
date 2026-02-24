"""
Self-Improving Loop - 让 AI Agent 自动进化

完整的 7 步自我改进闭环：
  1. Execute Task    → 执行任务（透明代理）
  2. Record Result   → 记录结果（Tracer）
  3. Analyze Failure → 分析失败模式（FailureAnalyzer）
  4. Generate Fix    → 生成改进建议（AutoEvolution）
  5. Auto Apply      → 自动应用低风险改进（AutoFixer）
  6. Verify Effect   → 验证效果（A/B 测试）
  7. Update Config   → 更新配置 + 自动回滚

Usage:
    from self_improving_loop import SelfImprovingLoop

    loop = SelfImprovingLoop()
    result = loop.execute_with_improvement(
        agent_id="coder-001",
        task="修复登录 bug",
        execute_fn=lambda: agent.run_task(task)
    )
"""

__version__ = "0.1.0"

from .core import SelfImprovingLoop
from .tracer import AgentTracer, TraceAnalyzer
from .rollback import AutoRollback
from .threshold import AdaptiveThreshold
from .notifier import Notifier, PrintNotifier

__all__ = [
    "SelfImprovingLoop",
    "AgentTracer",
    "TraceAnalyzer",
    "AutoRollback",
    "AdaptiveThreshold",
    "Notifier",
    "PrintNotifier",
]
