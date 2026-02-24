"""
Self-Improving Agent: 完整闭环
追踪 → 分析 → 修复 → 验证
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from agent_tracer import AgentTracer, TraceAnalyzer
from analyze_failures import FailureAnalyzer
from agent_auto_fixer import AgentAutoFixer

AIOS_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = AIOS_ROOT / "agent_system" / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


class SelfImprovingAgent:
    """自我改进 Agent 系统"""

    def __init__(self):
        self.tracer_analyzer = TraceAnalyzer()
        self.failure_analyzer = FailureAnalyzer()
        self.auto_fixer = AgentAutoFixer(auto_apply=False)  # 默认需要确认

    def run_improvement_cycle(
        self,
        days: int = 7,
        min_occurrences: int = 3,
        auto_apply: bool = False
    ) -> Dict:
        """
        运行一次完整的改进循环
        
        Args:
            days: 分析最近多少天的数据
            min_occurrences: 最少出现次数
            auto_apply: 是否自动应用低风险改进
        
        Returns:
            改进报告
        """
        print("=== Self-Improving Agent 改进循环 ===\n")
        print(f"分析周期: {days} 天")
        print(f"最少出现: {min_occurrences} 次")
        print(f"自动应用: {'是' if auto_apply else '否'}\n")

        cycle_report = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "days": days,
                "min_occurrences": min_occurrences,
                "auto_apply": auto_apply
            },
            "steps": {}
        }

        # Step 1: 分析追踪数据
        print("Step 1: 分析追踪数据...")
        trace_stats = self._analyze_traces()
        cycle_report["steps"]["trace_analysis"] = trace_stats
        print(f"  总追踪: {trace_stats['total_traces']}")
        print(f"  失败率: {trace_stats['failure_rate']:.1%}\n")

        # Step 2: 识别失败模式
        print("Step 2: 识别失败模式...")
        failure_report = self.failure_analyzer.analyze(days=days, min_occurrences=min_occurrences)
        cycle_report["steps"]["failure_analysis"] = {
            "patterns_found": len(failure_report["patterns"]),
            "improvements_suggested": len(failure_report["improvements"])
        }
        print(f"  识别模式: {len(failure_report['patterns'])}")
        print(f"  改进建议: {len(failure_report['improvements'])}\n")

        if not failure_report["improvements"]:
            print("✓ 未发现需要改进的模式，系统运行正常")
            cycle_report["status"] = "healthy"
            self._save_report(cycle_report)
            return cycle_report

        # Step 3: 应用修复
        print("Step 3: 应用修复...")
        self.auto_fixer.auto_apply = auto_apply
        fix_report = self.auto_fixer.analyze_and_fix(days=days, min_occurrences=min_occurrences)
        cycle_report["steps"]["fix_application"] = fix_report["summary"]
        print(f"  已应用: {fix_report['summary']['applied']}")
        print(f"  成功: {fix_report['summary']['success']}\n")

        # Step 4: 生成总结
        cycle_report["status"] = "improved" if fix_report["summary"]["success"] > 0 else "no_change"
        cycle_report["summary"] = self._generate_summary(cycle_report)

        # 保存报告
        self._save_report(cycle_report)

        print("=== 改进循环完成 ===")
        print(f"状态: {cycle_report['status']}")
        print(f"报告: {REPORT_DIR / f'cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json'}")

        return cycle_report

    def _analyze_traces(self) -> Dict:
        """分析追踪数据"""
        traces = self.tracer_analyzer.traces
        total = len(traces)
        failures = sum(1 for t in traces if not t.get("success"))

        return {
            "total_traces": total,
            "failures": failures,
            "failure_rate": failures / total if total > 0 else 0,
            "agents": list(set(t["agent_id"] for t in traces))
        }

    def _generate_summary(self, cycle_report: Dict) -> str:
        """生成人类可读的总结"""
        steps = cycle_report["steps"]
        trace = steps["trace_analysis"]
        failure = steps["failure_analysis"]
        fix = steps["fix_application"]

        summary = f"""
改进循环总结：
- 分析了 {trace['total_traces']} 条追踪记录，失败率 {trace['failure_rate']:.1%}
- 识别了 {failure['patterns_found']} 个失败模式
- 生成了 {failure['improvements_suggested']} 条改进建议
- 应用了 {fix['applied']} 个修复（成功 {fix['success']}，失败 {fix['failed']}）
- 跳过了 {fix['skipped']} 个需要人工审核的改进
"""
        return summary.strip()

    def _save_report(self, report: Dict):
        """保存改进报告"""
        report_path = REPORT_DIR / f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


def main():
    """命令行入口"""
    import sys

    # 解析参数
    auto_apply = "--auto" in sys.argv
    days = 7
    min_occurrences = 3

    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])
        elif arg == "--min" and i + 1 < len(sys.argv):
            min_occurrences = int(sys.argv[i + 1])

    # 运行改进循环
    agent = SelfImprovingAgent()
    report = agent.run_improvement_cycle(
        days=days,
        min_occurrences=min_occurrences,
        auto_apply=auto_apply
    )

    # 打印总结
    if "summary" in report:
        print(f"\n{report['summary']}")


if __name__ == "__main__":
    main()
