"""
Agent Tracer - 任务追踪系统

记录 Agent 执行的每个细节，用于后续分析和改进。
零外部依赖，纯标准库实现。
"""

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class AgentTracer:
    """Agent 任务追踪器"""

    def __init__(self, agent_id: str, trace_dir: Optional[Path] = None):
        self.agent_id = agent_id
        self.trace_dir = trace_dir or Path.cwd() / "data" / "traces"
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.trace_log = self.trace_dir / "agent_traces.jsonl"
        self.current_trace: Optional[Dict] = None

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
        self.current_trace["steps"].append({
            "step_name": step_name,
            "timestamp": datetime.now().isoformat(),
            "details": details or {},
        })

    def log_tool_call(self, tool_name: str, args: Dict, result: Any = None, error: str = None):
        """记录工具调用"""
        if not self.current_trace:
            return
        self.current_trace["tools_used"].append({
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "args": args,
            "result": str(result)[:200] if result else None,
            "error": error,
            "success": error is None,
        })

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

        with open(self.trace_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.current_trace, ensure_ascii=False) + "\n")

        self.current_trace = None

    def _generate_trace_id(self, task: str) -> str:
        content = f"{self.agent_id}:{task}:{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class TraceAnalyzer:
    """追踪数据分析器"""

    def __init__(self, trace_dir: Optional[Path] = None):
        self.trace_dir = trace_dir or Path.cwd() / "data" / "traces"
        self.trace_log = self.trace_dir / "agent_traces.jsonl"
        self.traces = self._load_traces()

    def _load_traces(self) -> List[Dict]:
        if not self.trace_log.exists():
            return []
        traces = []
        with open(self.trace_log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    traces.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return traces

    def reload(self):
        """重新加载追踪数据"""
        self.traces = self._load_traces()

    def get_failure_patterns(self, min_occurrences: int = 3) -> List[Dict]:
        """识别重复失败模式"""
        failures = [t for t in self.traces if not t.get("success")]
        error_groups: Dict[str, list] = {}
        for failure in failures:
            error = failure.get("error", "unknown")
            sig = self._generate_error_signature(error)
            error_groups.setdefault(sig, []).append(failure)

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
            return {"error": "No traces found"}

        total = len(agent_traces)
        successes = sum(1 for t in agent_traces if t.get("success"))
        avg_duration = sum(t.get("duration_sec", 0) for t in agent_traces) / total

        return {
            "agent_id": agent_id,
            "total_tasks": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": successes / total if total > 0 else 0,
            "avg_duration_sec": avg_duration,
        }

    def get_recent_traces(self, agent_id: str = None, hours: int = 24) -> List[Dict]:
        """获取最近 N 小时的追踪数据"""
        cutoff = datetime.now() - timedelta(hours=hours)
        traces = self.traces
        if agent_id:
            traces = [t for t in traces if t["agent_id"] == agent_id]
        return [
            t for t in traces
            if datetime.fromisoformat(t["start_time"]) > cutoff
        ]

    @staticmethod
    def _generate_error_signature(error: str) -> str:
        sig = re.sub(r'\d+', 'N', error)
        sig = re.sub(r'[A-Z]:\\[^\s]+', 'PATH', sig)
        sig = re.sub(r'/[^\s]+', 'PATH', sig)
        return sig[:100]
