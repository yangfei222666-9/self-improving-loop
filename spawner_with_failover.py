"""
AIOS Agent Spawner with Failover - 集成 Provider Manager
在 sessions_spawn 外层包装容灾机制
"""
import sys
from pathlib import Path

# 添加路径
AIOS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(AIOS_ROOT))

from core.provider_manager import get_provider_manager
from typing import Dict, Any, Optional


class AgentSpawnerWithFailover:
    """Agent Spawner - 集成容灾机制"""
    
    def __init__(self, sessions_spawn_fn):
        """
        初始化
        
        Args:
            sessions_spawn_fn: OpenClaw 的 sessions_spawn 函数
        """
        self.sessions_spawn = sessions_spawn_fn
        self.provider_manager = get_provider_manager()
    
    def spawn_with_failover(
        self,
        task: str,
        label: Optional[str] = None,
        model: Optional[str] = None,
        cleanup: str = "keep",
        runTimeoutSeconds: int = 300
    ) -> Dict[str, Any]:
        """
        创建 Agent（带 Failover）
        
        Args:
            task: 任务描述
            label: Agent 标签
            model: 模型名称
            cleanup: 清理策略
            runTimeoutSeconds: 超时时间
        
        Returns:
            创建结果
        """
        # 准备任务参数
        task_payload = {
            "task": task,
            "label": label,
            "model": model,
            "cleanup": cleanup,
            "runTimeoutSeconds": runTimeoutSeconds
        }
        
        # 定义执行函数
        def execute_spawn(provider_name: str, payload: Dict) -> Dict:
            """
            执行 Agent 创建
            
            Args:
                provider_name: Provider 名称（模型名）
                payload: 任务参数
            
            Returns:
                创建结果
            """
            # 使用指定的 provider（模型）
            result = self.sessions_spawn(
                task=payload["task"],
                label=payload["label"],
                model=provider_name,  # 使用 Failover 选择的模型
                cleanup=payload["cleanup"],
                runTimeoutSeconds=payload["runTimeoutSeconds"]
            )
            
            # 检查结果
            if not result or "error" in result:
                error_msg = result.get("error", "Unknown error") if result else "No response"
                raise Exception(f"Agent spawn failed: {error_msg}")
            
            return result
        
        # 使用 Provider Manager 执行（带 Failover + 重试 + DLQ）
        result = self.provider_manager.execute_with_failover(
            task_type="agent_spawn",
            task_payload=task_payload,
            execute_fn=execute_spawn
        )
        
        # 转换结果格式
        if result["success"]:
            return {
                "status": "spawned",
                "sessionKey": result["result"].get("sessionKey"),
                "provider": result["provider"],
                "attempt": result["attempt"]
            }
        else:
            return {
                "status": "failed",
                "error": result["error"],
                "dlq": result.get("dlq", False),
                "task_id": result.get("task_id")
            }


def create_spawner_with_failover(sessions_spawn_fn):
    """
    创建带 Failover 的 Spawner
    
    Args:
        sessions_spawn_fn: OpenClaw 的 sessions_spawn 函数
    
    Returns:
        AgentSpawnerWithFailover 实例
    """
    return AgentSpawnerWithFailover(sessions_spawn_fn)


# 测试用的 mock 函数
def mock_sessions_spawn(task, label=None, model=None, cleanup="keep", runTimeoutSeconds=300):
    """模拟 sessions_spawn（用于测试）"""
    import random
    
    # 模拟不同模型的行为
    if model == "claude-sonnet-4-6":
        # 模拟 502 错误
        return {"error": "FailoverError: The AI service is temporarily unavailable (HTTP 502)"}
    
    elif model == "claude-opus-4-6":
        # 模拟超时
        return {"error": "FailoverError: The AI service is temporarily unavailable (HTTP 502) (timeout)"}
    
    elif model == "claude-haiku-4-5":
        # 成功
        return {
            "sessionKey": f"session-{random.randint(1000, 9999)}",
            "status": "spawned"
        }
    
    else:
        return {"error": f"Unknown model: {model}"}


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("测试 Agent Spawner with Failover")
    print("=" * 60)
    
    # 创建 spawner
    spawner = create_spawner_with_failover(mock_sessions_spawn)
    
    # 测试 1: 正常创建（会 Failover 到 Haiku）
    print("\n测试 1: 创建 Agent（Sonnet 和 Opus 都会 502，自动 Failover 到 Haiku）")
    result = spawner.spawn_with_failover(
        task="帮我写一个 Python 爬虫",
        label="coder-test",
        model="claude-sonnet-4-6"  # 会失败，自动 Failover
    )
    
    print(f"\n结果:")
    print(f"  状态: {result['status']}")
    if result['status'] == 'spawned':
        print(f"  Session Key: {result['sessionKey']}")
        print(f"  使用的 Provider: {result['provider']}")
        print(f"  尝试次数: {result['attempt']}")
    else:
        print(f"  错误: {result['error']}")
        print(f"  进入 DLQ: {result.get('dlq', False)}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
