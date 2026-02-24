"""
AIOS Agent Spawner - 真实执行 sessions_spawn
在主 Agent 的心跳中调用此函数
"""

import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(__file__).parent.parent.parent
SPAWN_FILE = WORKSPACE / "aios" / "agent_system" / "spawn_requests.jsonl"
RESULTS_FILE = WORKSPACE / "aios" / "agent_system" / "spawn_results.jsonl"


def process_spawn_requests_for_heartbeat():
    """
    供主 Agent 心跳调用
    返回需要执行的 sessions_spawn 调用列表
    """
    if not SPAWN_FILE.exists():
        return []

    # 读取所有请求
    requests = []
    with open(SPAWN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                requests.append(json.loads(line))

    if not requests:
        return []

    # 清空请求文件
    SPAWN_FILE.write_text("", encoding="utf-8")

    return requests


def record_spawn_result(
    task_id: str, label: str, model: str, session_key: str = None, error: str = None
):
    """记录 spawn 结果"""
    result = {
        "task_id": task_id,
        "label": label,
        "model": model,
        "status": "success" if session_key else "error",
        "session_key": session_key,
        "error": error,
        "spawned_at": datetime.now().isoformat(),
    }

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
