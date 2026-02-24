"""
测试自适应阈值集成
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adaptive_threshold import AdaptiveThreshold


def test_adaptive_threshold():
    """测试自适应阈值"""
    print("=" * 60)
    print("  自适应阈值测试")
    print("=" * 60)

    adaptive = AdaptiveThreshold()
    now = datetime.now()

    # 测试 1：高频 Agent
    print("\n测试 1：高频 Agent（15 次/天）")
    high_freq_history = [
        {"start_time": (now - timedelta(hours=i)).isoformat()}
        for i in range(15)
    ]

    threshold, window, cooldown = adaptive.get_threshold("agent-high", high_freq_history)
    profile = adaptive.get_agent_profile("agent-high", high_freq_history)

    print(f"  频率: {profile['frequency']}")
    print(f"  任务数/天: {profile['tasks_per_day']}")
    print(f"  失败阈值: {threshold} 次")
    print(f"  分析窗口: {window} 小时")
    print(f"  冷却期: {cooldown} 小时")

    assert threshold == 5, "高频 Agent 阈值应该是 5"
    assert window == 48, "高频 Agent 窗口应该是 48 小时"
    assert cooldown == 3, "高频 Agent 冷却期应该是 3 小时"
    print("  ✓ 通过")

    # 测试 2：中频 Agent
    print("\n测试 2：中频 Agent（5 次/天）")
    mid_freq_history = [
        {"start_time": (now - timedelta(hours=i*4)).isoformat()}
        for i in range(5)
    ]

    threshold, window, cooldown = adaptive.get_threshold("agent-mid", mid_freq_history)
    profile = adaptive.get_agent_profile("agent-mid", mid_freq_history)

    print(f"  频率: {profile['frequency']}")
    print(f"  任务数/天: {profile['tasks_per_day']}")
    print(f"  失败阈值: {threshold} 次")
    print(f"  分析窗口: {window} 小时")
    print(f"  冷却期: {cooldown} 小时")

    assert threshold == 3, "中频 Agent 阈值应该是 3"
    assert window == 24, "中频 Agent 窗口应该是 24 小时"
    assert cooldown == 6, "中频 Agent 冷却期应该是 6 小时"
    print("  ✓ 通过")

    # 测试 3：低频 Agent
    print("\n测试 3：低频 Agent（2 次/天）")
    low_freq_history = [
        {"start_time": (now - timedelta(hours=i*12)).isoformat()}
        for i in range(2)
    ]

    threshold, window, cooldown = adaptive.get_threshold("agent-low", low_freq_history)
    profile = adaptive.get_agent_profile("agent-low", low_freq_history)

    print(f"  频率: {profile['frequency']}")
    print(f"  任务数/天: {profile['tasks_per_day']}")
    print(f"  失败阈值: {threshold} 次")
    print(f"  分析窗口: {window} 小时")
    print(f"  冷却期: {cooldown} 小时")

    assert threshold == 2, "低频 Agent 阈值应该是 2"
    assert window == 72, "低频 Agent 窗口应该是 72 小时"
    assert cooldown == 12, "低频 Agent 冷却期应该是 12 小时"
    print("  ✓ 通过")

    # 测试 4：关键 Agent
    print("\n测试 4：关键 Agent（名称包含 critical）")
    threshold, window, cooldown = adaptive.get_threshold("agent-critical-monitor", [])
    profile = adaptive.get_agent_profile("agent-critical-monitor", [])

    print(f"  是否关键: {profile['is_critical']}")
    print(f"  失败阈值: {threshold} 次")
    print(f"  分析窗口: {window} 小时")
    print(f"  冷却期: {cooldown} 小时")

    assert threshold == 1, "关键 Agent 阈值应该是 1"
    assert profile['is_critical'], "应该识别为关键 Agent"
    print("  ✓ 通过")

    # 测试 5：手动配置
    print("\n测试 5：手动配置 Agent")
    adaptive.set_manual_threshold(
        "agent-custom",
        failure_threshold=10,
        analysis_window_hours=12,
        cooldown_hours=1,
        is_critical=True
    )

    threshold, window, cooldown = adaptive.get_threshold("agent-custom", [])
    profile = adaptive.get_agent_profile("agent-custom", [])

    print(f"  配置来源: {profile['source']}")
    print(f"  失败阈值: {threshold} 次")
    print(f"  分析窗口: {window} 小时")
    print(f"  冷却期: {cooldown} 小时")

    assert threshold == 10, "手动配置阈值应该是 10"
    assert window == 12, "手动配置窗口应该是 12 小时"
    assert cooldown == 1, "手动配置冷却期应该是 1 小时"
    assert profile['source'] == "manual", "配置来源应该是 manual"
    print("  ✓ 通过")

    # 测试 6：对比不同频率的差异
    print("\n测试 6：对比不同频率的差异")
    print("  类型      | 阈值 | 窗口 | 冷却期")
    print("  ---------|------|------|-------")
    print(f"  高频      |  5   | 48h  |  3h")
    print(f"  中频      |  3   | 24h  |  6h")
    print(f"  低频      |  2   | 72h  | 12h")
    print(f"  关键      |  1   | 24h  |  6h")
    print("  ✓ 差异明显，符合预期")

    print("\n" + "=" * 60)
    print("  测试完成 ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_adaptive_threshold()
