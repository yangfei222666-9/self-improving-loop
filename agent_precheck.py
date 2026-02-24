"""
Agent Pre-Check: 启动前检查 AIOS 历史错误
让 Agent 从过去的错误中学习，避免重复犯错
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

AIOS_ROOT = Path(__file__).resolve().parent.parent
EVENTS_DIR = AIOS_ROOT / "events"
QUEUE_DIR = EVENTS_DIR / "queue"


def load_recent_errors(days: int = 7) -> List[Dict]:
    """加载最近 N 天的错误事件"""
    errors = []
    now = datetime.now()

    for i in range(days):
        date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        queue_file = QUEUE_DIR / f"{date}.jsonl"

        if not queue_file.exists():
            continue

        with open(queue_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if event.get("level") in ["ERR", "CRIT"]:
                        errors.append(event)
                except:
                    continue

    return errors


def extract_error_patterns(errors: List[Dict]) -> Dict[str, Any]:
    """从错误中提取模式"""
    patterns = {
        "network_errors": [],
        "api_errors": [],
        "timeout_errors": [],
        "rate_limit_errors": [],
        "other_errors": [],
    }

    for error in errors:
        msg = error.get("msg", "").lower()

        if "502" in msg or "network" in msg or "connection" in msg:
            patterns["network_errors"].append(error)
        elif "429" in msg or "rate limit" in msg or "限流" in msg:
            patterns["rate_limit_errors"].append(error)
        elif "timeout" in msg or "超时" in msg:
            patterns["timeout_errors"].append(error)
        elif "api" in msg or "401" in msg or "403" in msg:
            patterns["api_errors"].append(error)
        else:
            patterns["other_errors"].append(error)

    return patterns


def generate_agent_warnings(patterns: Dict[str, Any]) -> str:
    """生成给 Agent 的警告信息"""
    warnings = []

    if patterns["network_errors"]:
        count = len(patterns["network_errors"])
        warnings.append(
            f"⚠️ 最近发生了 {count} 次网络错误，执行网络请求时请增加重试机制"
        )

    if patterns["rate_limit_errors"]:
        count = len(patterns["rate_limit_errors"])
        warnings.append(
            f"⚠️ 最近发生了 {count} 次 API 限流，请降低请求频率或增加等待时间"
        )

    if patterns["timeout_errors"]:
        count = len(patterns["timeout_errors"])
        warnings.append(
            f"⚠️ 最近发生了 {count} 次超时错误，请增加超时时间或优化执行逻辑"
        )

    if patterns["api_errors"]:
        count = len(patterns["api_errors"])
        warnings.append(f"⚠️ 最近发生了 {count} 次 API 错误，请检查认证和权限")

    if not warnings:
        return "✅ 最近没有发现重大错误，可以正常执行"

    return "\n".join(warnings)


def agent_pre_check(task_description: str = "") -> Dict[str, Any]:
    """
    Agent 启动前预检查
    返回：历史错误、警告信息、建议
    """
    # 加载最近 7 天的错误
    errors = load_recent_errors(days=7)

    # 提取错误模式
    patterns = extract_error_patterns(errors)

    # 生成警告信息
    warnings = generate_agent_warnings(patterns)

    # 生成建议
    suggestions = []
    if patterns["network_errors"]:
        suggestions.append("使用 retry 机制，至少重试 3 次")
    if patterns["rate_limit_errors"]:
        suggestions.append("在请求之间增加延迟（至少 1 秒）")
    if patterns["timeout_errors"]:
        suggestions.append("增加超时时间到 60 秒以上")

    return {
        "total_errors": len(errors),
        "patterns": {k: len(v) for k, v in patterns.items()},
        "warnings": warnings,
        "suggestions": suggestions,
        "check_time": datetime.now().isoformat(),
    }


def inject_warnings_to_prompt(base_prompt: str, check_result: Dict) -> str:
    """将警告注入到 Agent 的 system prompt"""
    if check_result["total_errors"] == 0:
        return base_prompt

    warning_section = f"""

## ⚠️ 历史错误警告（最近 7 天）

{check_result["warnings"]}

**建议：**
{chr(10).join(f"- {s}" for s in check_result["suggestions"])}

请在执行任务时特别注意以上问题，避免重复错误。
"""

    return base_prompt + warning_section


# ── CLI ──

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        result = agent_pre_check()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 演示
        print("=" * 50)
        print("Agent Pre-Check 演示")
        print("=" * 50)

        result = agent_pre_check()

        print(f"\n📊 统计：")
        print(f"  总错误数: {result['total_errors']}")
        print(f"  错误分类: {result['patterns']}")

        print(f"\n{result['warnings']}")

        if result["suggestions"]:
            print(f"\n💡 建议：")
            for s in result["suggestions"]:
                print(f"  - {s}")
