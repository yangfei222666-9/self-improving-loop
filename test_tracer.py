"""
测试 Agent Tracer 和 Failure Analyzer
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_tracer import AgentTracer, TraceAnalyzer
from analyze_failures import FailureAnalyzer


def test_tracer():
    """测试追踪器"""
    print("=== 测试 Agent Tracer ===\n")

    # 模拟成功任务
    tracer = AgentTracer("agent_coder_001")
    tracer.start_task("修复登录 bug", context={"file": "auth.py"})
    tracer.log_step("读取文件")
    tracer.log_tool_call("read", {"path": "auth.py"}, result="file content...")
    tracer.log_step("修改代码")
    tracer.log_tool_call("edit", {"path": "auth.py", "old": "...", "new": "..."})
    tracer.end_task(success=True, metadata={"lines_changed": 3})
    print("✓ 成功任务已记录")

    # 模拟失败任务（超时）
    tracer = AgentTracer("agent_coder_001")
    tracer.start_task("优化数据库查询", context={"file": "db.py"})
    tracer.log_step("分析查询")
    tracer.log_tool_call("exec", {"command": "python analyze.py"}, error="Timeout after 30s")
    tracer.end_task(success=False, error="Timeout after 30s")
    print("✓ 失败任务已记录（超时）")

    # 模拟失败任务（网络错误）
    tracer = AgentTracer("agent_researcher_001")
    tracer.start_task("搜索文档", context={"query": "Python async"})
    tracer.log_tool_call("web_search", {"query": "Python async"}, error="502 Bad Gateway")
    tracer.end_task(success=False, error="502 Bad Gateway")
    print("✓ 失败任务已记录（网络错误）")

    # 再来几个相同的失败（模拟重复模式）
    for i in range(3):
        tracer = AgentTracer("agent_coder_001")
        tracer.start_task(f"任务 {i+1}", context={})
        tracer.log_tool_call("exec", {"command": "test"}, error="Timeout after 30s")
        tracer.end_task(success=False, error="Timeout after 30s")
    print("✓ 重复失败模式已记录（3次超时）\n")


def test_analyzer():
    """测试分析器"""
    print("=== 测试 Trace Analyzer ===\n")

    analyzer = TraceAnalyzer()

    # 获取失败模式
    patterns = analyzer.get_failure_patterns(min_occurrences=2)
    print(f"识别到 {len(patterns)} 个失败模式：")
    for p in patterns:
        print(f"  - {p['error_signature'][:50]}... (出现 {p['occurrences']} 次)")

    # 获取 Agent 统计
    stats = analyzer.get_agent_stats("agent_coder_001")
    print(f"\nAgent agent_coder_001 统计：")
    print(f"  总任务: {stats['total_tasks']}")
    print(f"  成功率: {stats['success_rate']:.1%}")
    print(f"  平均耗时: {stats['avg_duration_sec']:.2f}s")
    print()


def test_failure_analyzer():
    """测试失败分析器"""
    print("=== 测试 Failure Analyzer ===\n")

    analyzer = FailureAnalyzer()
    report = analyzer.analyze(days=7, min_occurrences=2)

    print(f"分析报告：")
    print(f"  总追踪数: {report['total_traces']}")
    print(f"  总失败数: {report['total_failures']}")
    print(f"  识别模式: {len(report['patterns'])}")
    print(f"  改进建议: {len(report['improvements'])}\n")

    if report["improvements"]:
        print("改进建议：")
        for i, improvement in enumerate(report["improvements"], 1):
            print(f"\n{i}. {improvement['description']}")
            print(f"   类型: {improvement['improvement_type']}")
            print(f"   优先级: {improvement['priority']}")
            print(f"   操作: {improvement['action']['change']}")


if __name__ == "__main__":
    print("开始测试...\n")
    test_tracer()
    test_analyzer()
    test_failure_analyzer()
    print("\n✓ 所有测试完成")
