import sys
sys.path.insert(0, 'C:/Users/A/.openclaw/workspace')
from aios.agent_system.sync_subagents import sync_from_subagents

# 真实的 subagents 数据
subagents_data = {
    'status': 'ok',
    'subagents': [
        {
            'label': 'aios-performance-analysis',
            'status': 'running',
            'sessionKey': 'agent:main:subagent:785365ce-6dec-4f12-bfc1-73b4d988f9a5'
        },
        {
            'label': 'aios-refactor-scheduler',
            'status': 'completed',
            'sessionKey': 'agent:main:subagent:3c930981-458b-4c66-a48a-510ada94c4d8'
        },
        {
            'label': 'aios-cleanup-script',
            'status': 'completed',
            'sessionKey': 'agent:main:subagent:0331e1a4-8e61-4af2-86f7-e5b4ecc60b08'
        },
        {
            'label': 'aios-analysis-task',
            'status': 'completed',
            'sessionKey': 'agent:main:subagent:1de4f409-35ca-486f-a706-a41143a64968'
        }
    ]
}

result = sync_from_subagents(subagents_data)
print(f"同步完成: 更新 {result['updated']} 个, 创建 {result['created']} 个, 总计 {result['total']} 个 Agent")
