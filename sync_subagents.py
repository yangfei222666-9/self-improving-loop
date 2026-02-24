"""
AIOS Agent System - 同步 OpenClaw 子 Agent 状态
将 sessions_spawn 创建的子 Agent 同步到 AIOS Agent System
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加路径
WORKSPACE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSPACE))

AGENTS_FILE = WORKSPACE / "aios" / "agent_system" / "data" / "agents.jsonl"


def load_agents():
    """加载现有 Agent"""
    if not AGENTS_FILE.exists():
        return []
    
    agents = []
    with open(AGENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                agents.append(json.loads(line))
    return agents


def save_agents(agents):
    """保存 Agent 列表"""
    AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AGENTS_FILE, "w", encoding="utf-8") as f:
        for agent in agents:
            f.write(json.dumps(agent, ensure_ascii=False) + "\n")


def sync_from_subagents(subagents_list):
    """
    从 subagents list 同步状态
    
    Args:
        subagents_list: subagents(action="list") 的返回结果
    """
    if subagents_list.get("status") != "ok":
        print(f"Error: {subagents_list.get('error')}")
        return
    
    # 加载现有 Agent
    agents = load_agents()
    agents_by_label = {a.get("label"): a for a in agents}
    
    # 同步子 Agent 状态
    subagents = subagents_list.get("subagents", [])
    updated = 0
    created = 0
    
    for sub in subagents:
        label = sub.get("label")
        status = sub.get("status")  # running/completed/failed
        session_key = sub.get("sessionKey")
        
        if not label:
            continue
        
        # 推断 Agent 类型
        template = "analyst"
        if "coder" in label.lower() or "code" in label.lower() or "refactor" in label.lower():
            template = "coder"
        elif "monitor" in label.lower():
            template = "monitor"
        elif "research" in label.lower():
            template = "researcher"
        
        # 推断任务描述
        task_desc = label.replace("-", " ").replace("_", " ").title()
        
        if label in agents_by_label:
            # 更新现有 Agent
            agent = agents_by_label[label]
            old_status = agent.get("status")
            
            # 映射状态
            if status == "running":
                agent["status"] = "active"
                agent["task_description"] = task_desc
            elif status == "completed":
                agent["status"] = "active"  # 保持 active，但清空任务
                agent["task_description"] = None
                # 更新统计
                stats = agent.get("stats", {})
                stats["tasks_completed"] = stats.get("tasks_completed", 0) + 1
                stats["last_active"] = datetime.now().isoformat()
                agent["stats"] = stats
            elif status == "failed":
                agent["status"] = "active"
                agent["task_description"] = None
            
            if old_status != agent["status"]:
                updated += 1
        else:
            # 创建新 Agent
            agent_id = f"{template}-{label.split('-')[-1]}" if '-' in label else f"{template}-{hash(label) % 1000000}"
            
            new_agent = {
                "id": agent_id,
                "label": label,
                "session_key": session_key,
                "template": template,
                "name": f"{template.title()} Agent",
                "status": "active" if status == "running" else "active",
                "task_description": task_desc if status == "running" else None,
                "created_at": datetime.now().isoformat(),
                "stats": {
                    "tasks_completed": 1 if status == "completed" else 0,
                    "success_rate": 1.0 if status == "completed" else 0.0,
                    "last_active": datetime.now().isoformat() if status != "running" else None
                }
            }
            
            agents.append(new_agent)
            agents_by_label[label] = new_agent
            created += 1
    
    # 保存
    save_agents(agents)
    
    return {
        "updated": updated,
        "created": created,
        "total": len(agents)
    }


def main():
    """命令行入口"""
    # 模拟 subagents 数据（实际使用时从 OpenClaw 获取）
    print("请在 OpenClaw 环境中调用此脚本")
    print("示例：")
    print("  from aios.agent_system.sync_subagents import sync_from_subagents")
    print("  result = sync_from_subagents(subagents(action='list'))")


if __name__ == "__main__":
    main()
