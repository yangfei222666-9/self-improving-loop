"""
Agent Tracer: 完整任务追踪系统
记录 Agent 执行的每个细节，用于后续分析和改进
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import hashlib

AIOS_ROOT = Path(__file__).resolve().parent.parent
TRACE_DIR = AIOS_ROOT / "agent_system" / "data" / "traces"
TRACE_DIR.mkdir(parents=True, exist_ok=True)

TRACE_LOG = TRACE_DIR / "agent_traces.jsonl"


class AgentTracer:
    """Agent 任务追踪器"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.current_trace = None

    def start_task(self, task: str, context: Dict[str, Any] = None):
        """开始追踪一个任务"""
        self.current_trace = {
            "trace_id": self._generate_trace_id(task),
            "agent_id": self.agent_id,
            "task": task,
            "context": context or {},
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration_sec": None,
            "success": None,
            "error": None,
            "tools_used": [],
            "steps": [],
            "metadata": {},
        }

    def log_step(self, step_name: str, details: Dict[str, Any] = None):
        """记录任务中的一个步骤"""
        if not self.current_trace:
            return

        step = {
            "step_name": step_name,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        }
        self.current_trace["steps"].append(step)

    def log_tool_call(self, tool_name: str, args: Dict, result: Any = None, error: str = None):
        """记录工具调用"""
        if not self.current_trace:
            return

        tool_call = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "args": args,
            "result": str(result)[:200] if result else None,  # 截断长结果
            "error": error,
            "success": error is None,
        }
        self.current_trace["tools_used"].append(tool_call)

    def end_task(self, success: bool, error: str = None, metadata: Dict[str, Any] = None):
        """结束任务追踪"""
        if not self.current_trace:
            return

        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.current_trace["start_time"])
        duration = (end_time - start_time).total_seconds()

        self.current_trace.update({
            "end_time": end_time.isoformat(),
            "duration_sec": duration,
            "success": success,
            "error": error,
            "metadata": metadata or {},
        })

        # 写入日志
        with open(TRACE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.current_trace, ensure_ascii=False) + "\n")

        self.current_trace = None

    def _generate_trace_id(self, task: str) -> str:
        """生成追踪 ID"""
        content = f"{self.agent_id}:{task}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class TraceAnalyzer:
    """追踪数据分析器"""

    def __init__(self):
        self.traces = self._load_traces()

    def _load_traces(self) -> List[Dict]:
        """加载所有追踪数据"""
        if not TRACE_LOG.exists():
            return []

        traces = []
        with open(TRACE_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    traces.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return traces

    def get_failure_patterns(self, min_occurrences: int = 3) -> List[Dict]:
        """识别重复失败模式"""
        failures = [t for t in self.traces if not t.get("success")]

        # 按错误类型分组
        error_groups = {}
        for failure in failures:
            error = failure.get("error", "unknown")
            error_sig = self._generate_error_signature(error)

            if error_sig not in error_groups:
                error_groups[error_sig] = []
            error_groups[error_sig].append(failure)

        # 筛选出现次数 >= min_occurrences 的模式
        patterns = []
        for sig, group in error_groups.items():
            if len(group) >= min_occurrences:
                patterns.append({
                    "error_signature": sig,
                    "occurrences": len(group),
                    "first_seen": group[0]["start_time"],
                    "last_seen": group[-1]["start_time"],
                    "affected_agents": list(set(t["agent_id"] for t in group)),
                    "sample_error": group[0]["error"],
                    "sample_task": group[0]["task"],
                })

        return sorted(patterns, key=lambda x: x["occurrences"], reverse=True)

    def get_agent_stats(self, agent_id: str) -> Dict:
        """获取特定 Agent 的统计数据"""
        agent_traces = [t for t in self.traces if t["agent_id"] == agent_id]

        if not agent_traces:
            return {"error": "No traces found for this agent"}

        total = len(agent_traces)
        successes = sum(1 for t in agent_traces if t.get("success"))
        failures = total - successes

        avg_duration = sum(t.get("duration_sec", 0) for t in agent_traces) / total

        return {
            "agent_id": agent_id,
            "total_tasks": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total if total > 0 else 0,
            "avg_duration_sec": avg_duration,
            "most_common_tools": self._get_most_common_tools(agent_traces),
        }

    def _get_most_common_tools(self, traces: List[Dict]) -> List[str]:
        """获取最常用的工具"""
        tool_counts = {}
        for trace in traces:
            for tool_call in trace.get("tools_used", []):
                tool = tool_call["tool"]
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
        return [tool for tool, _ in sorted_tools[:5]]

    def _generate_error_signature(self, error: str) -> str:
        """生成错误签名（用于分组相似错误）"""
        # 简化版：移除数字、路径等变化部分
        import re
        sig = re.sub(r'\d+', 'N', error)  # 数字替换为 N
        sig = re.sub(r'[A-Z]:\\[^\s]+', 'PATH', sig)  # Windows 路径
        sig = re.sub(r'/[^\s]+', 'PATH', sig)  # Unix 路径
        return sig[:100]  # 截断


def example_usage():
    """使用示例"""
    # 1. 追踪任务
    tracer = AgentTracer("agent_coder_001")

    tracer.start_task("修复登录 bug", context={"file": "auth.py", "line": 42})
    tracer.log_step("读取文件", {"file": "auth.py"})
    tracer.log_tool_call("read", {"path": "auth.py"}, result="file content...")
    tracer.log_step("分析代码", {"issue": "密码验证逻辑错误"})
    tracer.log_tool_call("edit", {"path": "auth.py", "old": "...", "new": "..."})
    tracer.end_task(success=True, metadata={"lines_changed": 3})

    # 2. 分析失败模式
    analyzer = TraceAnalyzer()
    patterns = analyzer.get_failure_patterns(min_occurrences=3)
    print("重复失败模式：")
    for p in patterns:
        print(f"  - {p['error_signature']} (出现 {p['occurrences']} 次)")

    # 3. 查看 Agent 统计
    stats = analyzer.get_agent_stats("agent_coder_001")
    print(f"\nAgent 统计：")
    print(f"  成功率: {stats['success_rate']:.1%}")
    print(f"  平均耗时: {stats['avg_duration_sec']:.1f}s")


if __name__ == "__main__":
    example_usage()
