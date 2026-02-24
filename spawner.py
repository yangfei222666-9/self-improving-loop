"""
AIOS Agent Spawner - 主 Agent 心跳检查并执行 spawn 请求
"""

import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(__file__).parent.parent.parent
SPAWN_FILE = WORKSPACE / "aios" / "agent_system" / "spawn_requests.jsonl"
RESULTS_FILE = WORKSPACE / "aios" / "agent_system" / "spawn_results.jsonl"


def check_and_spawn():
    """检查待执行的 spawn 请求并执行"""
    if not SPAWN_FILE.exists():
        print("SKIP no spawn requests")
        return

    # 读取所有请求
    requests = []
    with open(SPAWN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                requests.append(json.loads(line))

    if not requests:
        print("SKIP no spawn requests")
        return

    print(f"Found {len(requests)} spawn requests")

    # 清空请求文件
    SPAWN_FILE.write_text("", encoding="utf-8")

    # 执行每个请求
    for req in requests:
        task_id = req["task_id"]
        label = req["label"]
        message = req["message"]
        model = req["model"]

        print(f"Spawning {label} for task {task_id}...")
        print(f"  Model: {model}")
        print(f"  Message: {message[:60]}...")

        # 记录结果（实际执行时会有 session_key）
        result = {
            "task_id": task_id,
            "label": label,
            "model": model,
            "status": "spawned",
            "spawned_at": datetime.now().isoformat(),
            "note": "This is a placeholder - actual sessions_spawn will be called by main agent",
        }

        # 写入结果
        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(f"OK spawned {len(requests)} agents")


if __name__ == "__main__":
    check_and_spawn()
