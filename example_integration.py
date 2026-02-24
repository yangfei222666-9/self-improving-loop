"""
Self-Improving Loop 集成示例
展示如何在实际 Agent 中使用
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from self_improving_loop import SelfImprovingLoop


# ============================================================================
# 示例 1: 基础集成（包装执行函数）
# ============================================================================

class CoderAgent:
    """代码开发 Agent"""
    
    def __init__(self, agent_id="coder-001"):
        self.agent_id = agent_id
        self.loop = SelfImprovingLoop()
    
    def run_task(self, task):
        """执行任务（自动嵌入改进循环）"""
        return self.loop.execute_with_improvement(
            agent_id=self.agent_id,
            task=task,
            execute_fn=lambda: self._do_coding_task(task),
            context={"agent_type": "coder"}
        )
    
    def _do_coding_task(self, task):
        """实际的编码逻辑"""
        # 这里是你的实际任务逻辑
        print(f"执行编码任务: {task}")
        
        # 模拟任务执行
        if "bug" in task.lower():
            # 模拟修复 bug
            return {"status": "fixed", "files_changed": 3}
        else:
            # 模拟新功能开发
            return {"status": "completed", "lines_added": 150}


# ============================================================================
# 示例 2: 装饰器模式
# ============================================================================

from functools import wraps

def with_self_improvement(agent_id):
    """装饰器：自动嵌入 Self-Improving Loop"""
    loop = SelfImprovingLoop()
    
    def decorator(func):
        @wraps(func)
        def wrapper(task, *args, **kwargs):
            return loop.execute_with_improvement(
                agent_id=agent_id,
                task=task,
                execute_fn=lambda: func(task, *args, **kwargs)
            )
        return wrapper
    return decorator


@with_self_improvement("analyst-001")
def run_analysis_task(task):
    """数据分析任务（自动嵌入改进循环）"""
    print(f"执行分析任务: {task}")
    # 实际分析逻辑
    return {"status": "analyzed", "insights": 5}


# ============================================================================
# 示例 3: 集成到 Auto Dispatcher
# ============================================================================

class AutoDispatcher:
    """自动任务分发器（集成 Self-Improving Loop）"""
    
    def __init__(self):
        self.loop = SelfImprovingLoop()
        self.agents = {
            "coder": CoderAgent("coder-001"),
            "analyst": None,  # 使用装饰器模式
        }
    
    def dispatch_task(self, task_type, task):
        """分发任务到合适的 Agent"""
        if task_type == "code":
            agent = self.agents["coder"]
            return agent.run_task(task)
        
        elif task_type == "analysis":
            return run_analysis_task(task)
        
        else:
            raise ValueError(f"Unknown task type: {task_type}")


# ============================================================================
# 示例 4: 批量任务处理
# ============================================================================

def process_task_queue():
    """处理任务队列（每个任务自动嵌入改进循环）"""
    loop = SelfImprovingLoop()
    
    tasks = [
        {"agent_id": "coder-001", "task": "修复登录 bug"},
        {"agent_id": "coder-001", "task": "实现新功能"},
        {"agent_id": "analyst-001", "task": "分析用户数据"},
    ]
    
    results = []
    for task_info in tasks:
        result = loop.execute_with_improvement(
            agent_id=task_info["agent_id"],
            task=task_info["task"],
            execute_fn=lambda t=task_info: execute_task(t)
        )
        results.append(result)
    
    return results


def execute_task(task_info):
    """实际执行任务"""
    print(f"执行任务: {task_info['task']}")
    return {"status": "done"}


# ============================================================================
# 运行示例
# ============================================================================

def main():
    print("=" * 60)
    print("  Self-Improving Loop 集成示例")
    print("=" * 60)
    
    # 示例 1: 基础集成
    print("\n示例 1: 基础集成")
    agent = CoderAgent()
    result = agent.run_task("修复登录 bug")
    print(f"  结果: {result['success']}")
    print(f"  改进触发: {result['improvement_triggered']}")
    
    # 示例 2: 装饰器模式
    print("\n示例 2: 装饰器模式")
    result = run_analysis_task("分析用户行为")
    print(f"  结果: {result['success']}")
    
    # 示例 3: Auto Dispatcher
    print("\n示例 3: Auto Dispatcher")
    dispatcher = AutoDispatcher()
    result = dispatcher.dispatch_task("code", "实现新功能")
    print(f"  结果: {result['success']}")
    
    # 示例 4: 批量处理
    print("\n示例 4: 批量任务处理")
    results = process_task_queue()
    print(f"  处理了 {len(results)} 个任务")
    success_count = sum(1 for r in results if r["success"])
    print(f"  成功: {success_count}/{len(results)}")
    
    # 查看全局统计
    print("\n全局统计:")
    loop = SelfImprovingLoop()
    stats = loop.get_improvement_stats()
    print(f"  总 Agent: {stats['total_agents']}")
    print(f"  总改进次数: {stats['total_improvements']}")
    print(f"  已改进 Agent: {stats['agents_improved']}")


if __name__ == "__main__":
    main()
