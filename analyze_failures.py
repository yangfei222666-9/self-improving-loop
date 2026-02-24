"""
Failure Pattern Analyzer: 失败模式分析器
从追踪数据中识别重复失败模式，生成改进建议
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict

from agent_tracer import TraceAnalyzer

AIOS_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = AIOS_ROOT / "agent_system" / "data" / "analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

FAILURE_REPORT = ANALYSIS_DIR / "failure_patterns.json"


class FailureAnalyzer:
    """失败模式分析器"""

    def __init__(self):
        self.analyzer = TraceAnalyzer()

    def analyze(self, days: int = 7, min_occurrences: int = 3) -> Dict:
        """
        分析最近 N 天的失败模式
        
        Args:
            days: 分析最近多少天的数据
            min_occurrences: 最少出现次数（低于此值的模式会被忽略）
        
        Returns:
            分析报告
        """
        cutoff_time = datetime.now() - timedelta(days=days)

        # 筛选最近的追踪数据
        recent_traces = [
            t for t in self.analyzer.traces
            if datetime.fromisoformat(t["start_time"]) > cutoff_time
        ]

        # 识别失败模式
        patterns = self._identify_patterns(recent_traces, min_occurrences)

        # 生成改进建议
        improvements = self._generate_improvements(patterns)

        report = {
            "generated_at": datetime.now().isoformat(),
            "analysis_period_days": days,
            "total_traces": len(recent_traces),
            "total_failures": sum(1 for t in recent_traces if not t.get("success")),
            "patterns": patterns,
            "improvements": improvements,
        }

        # 保存报告
        with open(FAILURE_REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    def _identify_patterns(self, traces: List[Dict], min_occurrences: int) -> List[Dict]:
        """识别失败模式"""
        failures = [t for t in traces if not t.get("success")]

        # 按多个维度分组
        patterns = []

        # 1. 按错误类型分组
        error_groups = defaultdict(list)
        for failure in failures:
            error = failure.get("error", "unknown")
            error_sig = self._generate_error_signature(error)
            error_groups[error_sig].append(failure)

        for sig, group in error_groups.items():
            if len(group) >= min_occurrences:
                patterns.append({
                    "type": "error_pattern",
                    "signature": sig,
                    "occurrences": len(group),
                    "affected_agents": list(set(t["agent_id"] for t in group)),
                    "sample_error": group[0]["error"],
                    "first_seen": group[0]["start_time"],
                    "last_seen": group[-1]["start_time"],
                })

        # 2. 按 Agent 分组（识别特定 Agent 的问题）
        agent_failures = defaultdict(list)
        for failure in failures:
            agent_failures[failure["agent_id"]].append(failure)

        for agent_id, group in agent_failures.items():
            if len(group) >= min_occurrences:
                patterns.append({
                    "type": "agent_pattern",
                    "agent_id": agent_id,
                    "occurrences": len(group),
                    "failure_rate": len(group) / len([t for t in traces if t["agent_id"] == agent_id]),
                    "common_errors": self._get_common_errors(group),
                })

        # 3. 按工具调用失败分组
        tool_failures = defaultdict(list)
        for failure in failures:
            for tool_call in failure.get("tools_used", []):
                if not tool_call.get("success"):
                    tool_failures[tool_call["tool"]].append(failure)

        for tool, group in tool_failures.items():
            if len(group) >= min_occurrences:
                patterns.append({
                    "type": "tool_pattern",
                    "tool": tool,
                    "occurrences": len(group),
                    "common_errors": self._get_common_errors(group),
                })

        return patterns

    def _generate_improvements(self, patterns: List[Dict]) -> List[Dict]:
        """根据失败模式生成改进建议"""
        improvements = []

        for pattern in patterns:
            if pattern["type"] == "error_pattern":
                improvement = self._suggest_error_fix(pattern)
            elif pattern["type"] == "agent_pattern":
                improvement = self._suggest_agent_fix(pattern)
            elif pattern["type"] == "tool_pattern":
                improvement = self._suggest_tool_fix(pattern)
            else:
                continue

            if improvement:
                improvements.append(improvement)

        return improvements

    def _suggest_error_fix(self, pattern: Dict) -> Dict:
        """针对错误模式提出改进建议"""
        error = pattern["sample_error"].lower()

        # 规则库：错误类型 → 改进建议
        if "timeout" in error or "超时" in error:
            return {
                "pattern_type": "error_pattern",
                "pattern_signature": pattern["signature"],
                "improvement_type": "increase_timeout",
                "description": "检测到频繁超时，建议增加超时时间",
                "action": {
                    "type": "config_change",
                    "target": "timeout",
                    "change": "increase by 50%",
                },
                "priority": "high",
                "risk": "low",
            }

        elif "502" in error or "503" in error or "network" in error:
            return {
                "pattern_type": "error_pattern",
                "pattern_signature": pattern["signature"],
                "improvement_type": "add_retry",
                "description": "检测到网络错误，建议增加重试机制",
                "action": {
                    "type": "code_change",
                    "target": "network_calls",
                    "change": "add retry with exponential backoff (3 attempts)",
                },
                "priority": "high",
                "risk": "low",
            }

        elif "429" in error or "rate limit" in error:
            return {
                "pattern_type": "error_pattern",
                "pattern_signature": pattern["signature"],
                "improvement_type": "rate_limiting",
                "description": "检测到限流错误，建议降低请求频率",
                "action": {
                    "type": "config_change",
                    "target": "request_rate",
                "change": "add delay between requests (1-2 seconds)",
                },
                "priority": "medium",
                "risk": "low",
            }

        elif "memory" in error or "内存" in error:
            return {
                "pattern_type": "error_pattern",
                "pattern_signature": pattern["signature"],
                "improvement_type": "memory_optimization",
                "description": "检测到内存问题，建议优化内存使用",
                "action": {
                    "type": "code_change",
                    "target": "memory_usage",
                    "change": "add memory cleanup or reduce batch size",
                },
                "priority": "high",
                "risk": "medium",
            }

        return None

    def _suggest_agent_fix(self, pattern: Dict) -> Dict:
        """针对特定 Agent 的问题提出改进建议"""
        failure_rate = pattern["failure_rate"]

        if failure_rate > 0.5:  # 失败率超过 50%
            return {
                "pattern_type": "agent_pattern",
                "agent_id": pattern["agent_id"],
                "improvement_type": "agent_degradation",
                "description": f"Agent {pattern['agent_id']} 失败率过高 ({failure_rate:.1%})，建议降级或重启",
                "action": {
                    "type": "agent_action",
                    "target": pattern["agent_id"],
                    "change": "降低优先级或触发重启",
                },
                "priority": "critical",
                "risk": "low",
            }

        return None

    def _suggest_tool_fix(self, pattern: Dict) -> Dict:
        """针对工具调用失败提出改进建议"""
        return {
            "pattern_type": "tool_pattern",
            "tool": pattern["tool"],
            "improvement_type": "tool_fallback",
            "description": f"工具 {pattern['tool']} 频繁失败，建议添加备用方案",
            "action": {
                "type": "code_change",
                "target": pattern["tool"],
                "change": "add fallback tool or error handling",
            },
            "priority": "medium",
            "risk": "low",
        }

    def _generate_error_signature(self, error: str) -> str:
        """生成错误签名"""
        import re
        sig = re.sub(r'\d+', 'N', error)
        sig = re.sub(r'[A-Z]:\\[^\s]+', 'PATH', sig)
        sig = re.sub(r'/[^\s]+', 'PATH', sig)
        return sig[:100]

    def _get_common_errors(self, failures: List[Dict]) -> List[str]:
        """获取最常见的错误"""
        error_counts = defaultdict(int)
        for failure in failures:
            error = failure.get("error", "unknown")
            error_counts[error] += 1

        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [error for error, _ in sorted_errors[:3]]


def main():
    """命令行入口"""
    import sys

    analyzer = FailureAnalyzer()

    # 解析参数
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    min_occurrences = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    print(f"分析最近 {days} 天的失败模式（最少出现 {min_occurrences} 次）...\n")

    report = analyzer.analyze(days=days, min_occurrences=min_occurrences)

    print(f"总追踪数: {report['total_traces']}")
    print(f"总失败数: {report['total_failures']}")
    print(f"识别模式: {len(report['patterns'])}")
    print(f"改进建议: {len(report['improvements'])}\n")

    if report["improvements"]:
        print("改进建议：")
        for i, improvement in enumerate(report["improvements"], 1):
            print(f"\n{i}. {improvement['description']}")
            print(f"   类型: {improvement['improvement_type']}")
            print(f"   优先级: {improvement['priority']}")
            print(f"   风险: {improvement['risk']}")
            print(f"   操作: {improvement['action']['change']}")

    print(f"\n完整报告已保存到: {FAILURE_REPORT}")


if __name__ == "__main__":
    main()
