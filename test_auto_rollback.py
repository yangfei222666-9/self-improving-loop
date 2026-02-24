"""
测试自动回滚功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auto_rollback import AutoRollback


def test_auto_rollback():
    """测试自动回滚"""
    print("=" * 60)
    print("  自动回滚测试")
    print("=" * 60)

    rollback = AutoRollback()

    # 1. 备份配置
    print("\n1. 备份配置...")
    agent_id = "test-rollback-001"
    config = {
        "timeout": 30,
        "retry": 3,
        "priority": 1.0,
    }
    improvement_id = "improvement_test_001"

    backup_id = rollback.backup_config(agent_id, config, improvement_id)
    print(f"   ✓ 备份成功: {backup_id}")

    # 2. 测试场景 1：成功率下降
    print("\n2. 测试场景 1：成功率下降 >10%...")
    before_metrics = {
        "success_rate": 0.80,
        "avg_duration_sec": 10.0,
    }
    after_metrics = {
        "success_rate": 0.65,  # 下降 15%
        "avg_duration_sec": 10.0,
    }

    should_rollback, reason = rollback.should_rollback(
        agent_id, improvement_id, before_metrics, after_metrics
    )
    print(f"   应该回滚: {should_rollback}")
    print(f"   原因: {reason}")
    assert should_rollback, "应该触发回滚"

    # 3. 测试场景 2：耗时增加
    print("\n3. 测试场景 2：耗时增加 >20%...")
    before_metrics = {
        "success_rate": 0.80,
        "avg_duration_sec": 10.0,
    }
    after_metrics = {
        "success_rate": 0.80,
        "avg_duration_sec": 13.0,  # 增加 30%
    }

    should_rollback, reason = rollback.should_rollback(
        agent_id, improvement_id, before_metrics, after_metrics
    )
    print(f"   应该回滚: {should_rollback}")
    print(f"   原因: {reason}")
    assert should_rollback, "应该触发回滚"

    # 4. 测试场景 3：连续失败
    print("\n4. 测试场景 3：连续失败 ≥5 次...")
    before_metrics = {
        "success_rate": 0.80,
        "avg_duration_sec": 10.0,
    }
    after_metrics = {
        "success_rate": 0.75,
        "avg_duration_sec": 10.0,
        "consecutive_failures": 5,
    }

    should_rollback, reason = rollback.should_rollback(
        agent_id, improvement_id, before_metrics, after_metrics
    )
    print(f"   应该回滚: {should_rollback}")
    print(f"   原因: {reason}")
    assert should_rollback, "应该触发回滚"

    # 5. 测试场景 4：效果良好
    print("\n5. 测试场景 4：效果良好...")
    before_metrics = {
        "success_rate": 0.80,
        "avg_duration_sec": 10.0,
    }
    after_metrics = {
        "success_rate": 0.85,  # 提升 5%
        "avg_duration_sec": 9.0,  # 减少 10%
    }

    should_rollback, reason = rollback.should_rollback(
        agent_id, improvement_id, before_metrics, after_metrics
    )
    print(f"   应该回滚: {should_rollback}")
    print(f"   原因: {reason}")
    assert not should_rollback, "不应该触发回滚"

    # 6. 执行回滚
    print("\n6. 执行回滚...")
    result = rollback.rollback(agent_id, backup_id)
    print(f"   回滚成功: {result['success']}")
    if result["success"]:
        print(f"   备份 ID: {result['backup_id']}")
        print(f"   改进 ID: {result['improvement_id']}")

    # 7. 查看统计
    print("\n7. 查看统计...")
    stats = rollback.get_stats()
    print(f"   总回滚次数: {stats['total_rollbacks']}")
    print(f"   回滚 Agent 数: {stats['agents_rolled_back']}")
    print(f"   回滚 Agent: {stats['agents']}")

    # 8. 查看历史
    print("\n8. 查看回滚历史...")
    history = rollback.get_rollback_history(agent_id)
    print(f"   历史记录数: {len(history)}")
    for entry in history:
        print(f"   - {entry['rollback_id']}: {entry['timestamp']}")

    print("\n" + "=" * 60)
    print("  测试完成 ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_auto_rollback()
