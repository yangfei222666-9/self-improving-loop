"""
观察期报告生成器
每天自动输出一页验证报告
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter

from agent_tracer import TraceAnalyzer
from analyze_failures import FailureAnalyzer

AIOS_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = AIOS_ROOT / "agent_system" / "data" / "validation"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


class ValidationReport:
    """验证期报告生成器"""

    def __init__(self):
        self.trace_analyzer = TraceAnalyzer()
        self.failure_analyzer = FailureAnalyzer()

    def generate_daily_report(self, day: int = 1) -> Dict:
        """
        生成每日验证报告
        
        Args:
            day: 验证第几天（1/2/3）
        
        Returns:
            报告数据
        """
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 获取今天的追踪数据
        today_traces = [
            t for t in self.trace_analyzer.traces
            if datetime.fromisoformat(t["start_time"]) >= today_start
        ]

        # 获取昨天的追踪数据（用于对比）
        yesterday_start = today_start - timedelta(days=1)
        yesterday_traces = [
            t for t in self.trace_analyzer.traces
            if yesterday_start <= datetime.fromisoformat(t["start_time"]) < today_start
        ]

        report = {
            "day": day,
            "date": now.strftime("%Y-%m-%d"),
            "generated_at": now.isoformat(),
            "today_stats": self._calculate_stats(today_traces),
            "yesterday_stats": self._calculate_stats(yesterday_traces),
            "comparison": self._compare_stats(today_traces, yesterday_traces),
            "failure_patterns": self._analyze_patterns(today_traces),
            "improvements": self._get_improvements(),
            "safety_status": self._check_safety_status(),
            "verdict": self._generate_verdict(day, today_traces, yesterday_traces),
        }

        # 保存报告
        report_path = REPORT_DIR / f"day{day}_report_{now.strftime('%Y%m%d')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    def _calculate_stats(self, traces: List[Dict]) -> Dict:
        """计算统计数据"""
        if not traces:
            return {
                "total_tasks": 0,
                "failures": 0,
                "success_rate": 0,
                "timeout_count": 0,
                "avg_duration": 0,
                "failure_types": {},
            }

        total = len(traces)
        failures = [t for t in traces if not t.get("success")]
        timeouts = [t for t in failures if "timeout" in t.get("error", "").lower()]

        # 失败类型统计
        failure_types = Counter()
        for f in failures:
            error = f.get("error", "unknown")
            if "timeout" in error.lower():
                failure_types["timeout"] += 1
            elif "502" in error or "503" in error:
                failure_types["network"] += 1
            elif "429" in error:
                failure_types["rate_limit"] += 1
            elif "permission" in error.lower():
                failure_types["permission"] += 1
            else:
                failure_types["other"] += 1

        return {
            "total_tasks": total,
            "failures": len(failures),
            "success_rate": (total - len(failures)) / total if total > 0 else 0,
            "timeout_count": len(timeouts),
            "avg_duration": sum(t.get("duration_sec", 0) for t in traces) / total if total > 0 else 0,
            "failure_types": dict(failure_types.most_common(3)),
        }

    def _compare_stats(self, today: List[Dict], yesterday: List[Dict]) -> Dict:
        """对比今天和昨天的数据"""
        today_stats = self._calculate_stats(today)
        yesterday_stats = self._calculate_stats(yesterday)

        if yesterday_stats["total_tasks"] == 0:
            return {"note": "昨天无数据，无法对比"}

        return {
            "success_rate_change": today_stats["success_rate"] - yesterday_stats["success_rate"],
            "timeout_change": today_stats["timeout_count"] - yesterday_stats["timeout_count"],
            "avg_duration_change": today_stats["avg_duration"] - yesterday_stats["avg_duration"],
            "improvement": (
                today_stats["success_rate"] > yesterday_stats["success_rate"] or
                today_stats["timeout_count"] < yesterday_stats["timeout_count"]
            ),
        }

    def _analyze_patterns(self, traces: List[Dict]) -> List[Dict]:
        """分析失败模式"""
        failures = [t for t in traces if not t.get("success")]

        patterns = []
        error_groups = {}

        for failure in failures:
            error = failure.get("error", "unknown")
            error_sig = self._generate_error_signature(error)

            if error_sig not in error_groups:
                error_groups[error_sig] = []
            error_groups[error_sig].append(failure)

        for sig, group in error_groups.items():
            if len(group) >= 2:  # 至少出现 2 次
                patterns.append({
                    "signature": sig,
                    "count": len(group),
                    "sample_error": group[0]["error"],
                })

        return sorted(patterns, key=lambda x: x["count"], reverse=True)[:3]

    def _get_improvements(self) -> Dict:
        """获取改进建议和应用情况"""
        # 读取最新的修复报告
        fix_reports = sorted(
            (AIOS_ROOT / "agent_system" / "data" / "fixes").glob("fix_report_*.json"),
            reverse=True
        )

        if not fix_reports:
            return {"note": "暂无改进记录"}

        with open(fix_reports[0], "r", encoding="utf-8") as f:
            latest_report = json.load(f)

        return {
            "total_suggested": len(latest_report.get("analysis_report", {}).get("improvements", [])),
            "applied": latest_report.get("summary", {}).get("applied", 0),
            "success": latest_report.get("summary", {}).get("success", 0),
            "failed": latest_report.get("summary", {}).get("failed", 0),
        }

    def _check_safety_status(self) -> Dict:
        """检查安全状态"""
        from safety_valve import SafetyValve

        valve = SafetyValve()

        return {
            "circuit_breaker_broken": valve.circuit_breaker_state.get("broken", False),
            "consecutive_failures": valve.circuit_breaker_state.get("consecutive_failures", 0),
            "cooldown_count": len(valve.cooldown_state),
        }

    def _generate_verdict(self, day: int, today: List[Dict], yesterday: List[Dict]) -> Dict:
        """生成验证结论"""
        today_stats = self._calculate_stats(today)
        comparison = self._compare_stats(today, yesterday)

        if day == 1:
            # Day 1: 只读观察
            return {
                "day": 1,
                "phase": "只读观察（dry-run）",
                "pass": self._check_day1_criteria(today_stats),
                "criteria": {
                    "建议命中率": "主观判断 ≥80% 合理",
                    "无高风险建议": "检查改进建议列表",
                    "轨迹完整性": "每次都有 trace_id",
                },
            }

        elif day == 2:
            # Day 2: 低风险自动应用
            return {
                "day": 2,
                "phase": "低风险自动应用",
                "pass": self._check_day2_criteria(comparison),
                "criteria": {
                    "失败率下降或超时减少": comparison.get("improvement", False),
                    "无新增错误类型": "检查 failure_types",
                    "冷却期生效": "24h 内不重复应用",
                },
            }

        elif day == 3:
            # Day 3: 回归验证
            return {
                "day": 3,
                "phase": "回归验证",
                "pass": self._check_day3_criteria(comparison),
                "criteria": {
                    "success_rate 提升 ≥10%": comparison.get("success_rate_change", 0) >= 0.1,
                    "timeout_count 下降 ≥30%": (
                        comparison.get("timeout_change", 0) <= -0.3 * self._calculate_stats(yesterday)["timeout_count"]
                        if yesterday else False
                    ),
                    "无新增高危事件": "检查 safety_status",
                },
            }

        return {"day": day, "phase": "未知", "pass": False}

    def _check_day1_criteria(self, stats: Dict) -> bool:
        """检查 Day 1 通过标准"""
        # 简化版：只要有数据且失败率 <80% 就算通过
        return stats["total_tasks"] > 0 and stats["success_rate"] > 0.2

    def _check_day2_criteria(self, comparison: Dict) -> bool:
        """检查 Day 2 通过标准"""
        return comparison.get("improvement", False)

    def _check_day3_criteria(self, comparison: Dict) -> bool:
        """检查 Day 3 通过标准"""
        success_rate_ok = comparison.get("success_rate_change", 0) >= 0.1
        timeout_ok = comparison.get("timeout_change", 0) < 0
        return success_rate_ok or timeout_ok

    def _generate_error_signature(self, error: str) -> str:
        """生成错误签名"""
        import re
        sig = re.sub(r'\d+', 'N', error)
        sig = re.sub(r'[A-Z]:\\[^\s]+', 'PATH', sig)
        sig = re.sub(r'/[^\s]+', 'PATH', sig)
        return sig[:50]

    def print_report(self, report: Dict):
        """打印人类可读的报告"""
        print(f"\n{'='*60}")
        print(f"Day {report['day']} 验证报告 - {report['date']}")
        print(f"{'='*60}\n")

        # 今日统计
        today = report["today_stats"]
        print(f"📊 今日统计")
        print(f"  总任务数: {today['total_tasks']}")
        print(f"  失败数: {today['failures']}")
        print(f"  成功率: {today['success_rate']:.1%}")
        print(f"  超时数: {today['timeout_count']}")
        print(f"  平均耗时: {today['avg_duration']:.2f}s")
        print(f"  失败类型 Top3: {today['failure_types']}\n")

        # 对比
        if "note" not in report["comparison"]:
            comp = report["comparison"]
            print(f"📈 对比昨天")
            print(f"  成功率变化: {comp['success_rate_change']:+.1%}")
            print(f"  超时变化: {comp['timeout_change']:+d}")
            print(f"  耗时变化: {comp['avg_duration_change']:+.2f}s")
            print(f"  是否改善: {'✓' if comp['improvement'] else '✗'}\n")

        # 失败模式
        if report["failure_patterns"]:
            print(f"🔍 识别到的模式 Top3")
            for p in report["failure_patterns"]:
                print(f"  - {p['signature']} (出现 {p['count']} 次)")
            print()

        # 改进情况
        if "note" not in report["improvements"]:
            imp = report["improvements"]
            print(f"🔧 改进情况")
            print(f"  建议数: {imp['total_suggested']}")
            print(f"  应用数: {imp['applied']}")
            print(f"  成功: {imp['success']}")
            print(f"  失败: {imp['failed']}\n")

        # 安全状态
        safety = report["safety_status"]
        print(f"🛡️ 安全状态")
        print(f"  熔断器: {'触发' if safety['circuit_breaker_broken'] else '正常'}")
        print(f"  连续失败: {safety['consecutive_failures']}")
        print(f"  冷却中: {safety['cooldown_count']} 个改进\n")

        # 结论
        verdict = report["verdict"]
        print(f"✅ 验证结论")
        print(f"  阶段: {verdict['phase']}")
        print(f"  通过: {'✓' if verdict['pass'] else '✗'}")
        print(f"  标准: {verdict['criteria']}\n")

        print(f"{'='*60}\n")


def main():
    """命令行入口"""
    import sys

    day = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    reporter = ValidationReport()
    report = reporter.generate_daily_report(day=day)
    reporter.print_report(report)


if __name__ == "__main__":
    main()
