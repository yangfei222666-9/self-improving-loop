"""
Self-Improving Loop 心跳集成
每次心跳检查改进统计，定期报告
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))

from self_improving_loop import SelfImprovingLoop

WORKSPACE = Path.home() / ".openclaw" / "workspace"
STATE_FILE = WORKSPACE / "memory" / "selflearn-state.json"


def load_state():
    """加载状态文件"""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    """保存状态文件"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def should_report():
    """检查是否应该报告（每天一次）"""
    state = load_state()
    last_report = state.get("last_self_improving_report")

    if not last_report:
        return True

    last_time = datetime.fromisoformat(last_report)
    return (datetime.now() - last_time) > timedelta(hours=24)


def main():
    """心跳入口"""
    loop = SelfImprovingLoop()

    # 获取全局统计
    stats = loop.get_improvement_stats()

    # 检查是否有新的改进
    state = load_state()
    last_count = state.get("last_improvement_count", 0)
    current_count = stats["total_improvements"]

    if current_count > last_count:
        # 有新的改进
        new_improvements = current_count - last_count
        print(f"SELF_IMPROVING:+{new_improvements}")
        print(f"\n🔧 {new_improvements} 个 Agent 应用了自动改进")

        # 更新计数
        state["last_improvement_count"] = current_count
        save_state(state)

    elif should_report():
        # 定期报告
        print("SELF_IMPROVING_OK")
        print(f"\n📊 Self-Improving Loop 统计:")
        print(f"  总 Agent: {stats['total_agents']}")
        print(f"  总改进次数: {stats['total_improvements']}")
        print(f"  已改进 Agent: {len(stats['agents_improved'])}")

        # 更新报告时间
        state["last_self_improving_report"] = datetime.now().isoformat()
        save_state(state)

    else:
        # 静默
        print("HEARTBEAT_OK")


if __name__ == "__main__":
    main()
