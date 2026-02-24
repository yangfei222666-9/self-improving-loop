"""
测试 Auto Dispatcher + Self-Improving Loop 集成
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auto_dispatcher import AutoDispatcher

def test_integration():
    """测试完整集成"""
    workspace = Path(__file__).parent.parent.parent
    dispatcher = AutoDispatcher(workspace)
    
    print("=" * 60)
    print("  Auto Dispatcher + Self-Improving Loop 集成测试")
    print("=" * 60)
    
    # 1. 检查状态
    print("\n1. 检查初始状态...")
    status = dispatcher.status()
    print(f"   队列大小: {status['queue_size']}")
    print(f"   Self-Improving Loop: {'✓ 已启用' if status.get('self_improving') else '✗ 未启用'}")
    
    if status.get('self_improving'):
        stats = status['self_improving']
        print(f"   总 Agent: {stats.get('total_agents', 0)}")
        print(f"   总改进次数: {stats.get('total_improvements', 0)}")
    
    # 2. 添加测试任务
    print("\n2. 添加测试任务...")
    test_tasks = [
        {"type": "code", "message": "测试任务 1: 修复 bug", "priority": "high"},
        {"type": "analysis", "message": "测试任务 2: 分析数据", "priority": "normal"},
        {"type": "monitor", "message": "测试任务 3: 检查系统", "priority": "low"},
    ]
    
    for task in test_tasks:
        dispatcher.enqueue_task(task)
        print(f"   ✓ 已入队: {task['message']}")
    
    # 3. 处理队列
    print("\n3. 处理任务队列...")
    results = dispatcher.process_queue(max_tasks=3)
    print(f"   处理了 {len(results)} 个任务")
    
    for r in results:
        task_type = r['type']
        message = r['message'][:40]
        result_status = r['result']['status']
        print(f"   - {task_type}: {message}... → {result_status}")
    
    # 4. 检查最终状态
    print("\n4. 检查最终状态...")
    status = dispatcher.status()
    print(f"   队列大小: {status['queue_size']}")
    
    if status.get('self_improving'):
        stats = status['self_improving']
        print(f"   总改进次数: {stats.get('total_improvements', 0)}")
    
    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_integration()
