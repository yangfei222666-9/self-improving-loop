"""
Agent Auto-Fixer: 自动修复 Agent 问题
根据失败分析自动应用改进方案
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from analyze_failures import FailureAnalyzer

AIOS_ROOT = Path(__file__).resolve().parent.parent
FIX_DIR = AIOS_ROOT / "agent_system" / "data" / "fixes"
FIX_DIR.mkdir(parents=True, exist_ok=True)

FIX_LOG = FIX_DIR / "fix_history.jsonl"
AGENT_CONFIG = AIOS_ROOT / "agent_system" / "data" / "agent_configs.json"


class AgentAutoFixer:
    """Agent 自动修复器"""

    def __init__(self, auto_apply: bool = False):
        """
        Args:
            auto_apply: 是否自动应用低风险改进（默认 False，需要人工确认）
        """
        self.auto_apply = auto_apply
        self.analyzer = FailureAnalyzer()

    def analyze_and_fix(self, days: int = 7, min_occurrences: int = 3) -> Dict:
        """
        分析失败模式并应用修复
        
        Returns:
            修复报告
        """
        # 1. 分析失败模式
        print(f"分析最近 {days} 天的失败模式...")
        report = self.analyzer.analyze(days=days, min_occurrences=min_occurrences)

        if not report["improvements"]:
            print("未发现需要改进的模式")
            return {"status": "no_improvements", "report": report}

        print(f"发现 {len(report['improvements'])} 条改进建议\n")

        # 2. 分类改进建议
        low_risk = [i for i in report["improvements"] if i["risk"] == "low"]
        medium_risk = [i for i in report["improvements"] if i["risk"] == "medium"]
        high_risk = [i for i in report["improvements"] if i["risk"] == "high"]

        print(f"低风险: {len(low_risk)}, 中风险: {len(medium_risk)}, 高风险: {len(high_risk)}")

        # 3. 应用修复
        applied_fixes = []
        skipped_fixes = []

        for improvement in report["improvements"]:
            if improvement["risk"] == "low" and self.auto_apply:
                # 自动应用低风险改进
                result = self._apply_fix(improvement)
                applied_fixes.append(result)
            elif improvement["risk"] == "low":
                # 低风险但需要确认
                print(f"\n[低风险] {improvement['description']}")
                print(f"  操作: {improvement['action']['change']}")
                confirm = input("  是否应用? (y/n): ").lower()
                if confirm == 'y':
                    result = self._apply_fix(improvement)
                    applied_fixes.append(result)
                else:
                    skipped_fixes.append(improvement)
            else:
                # 中高风险需要人工审核
                print(f"\n[{improvement['risk'].upper()}风险] {improvement['description']}")
                print(f"  操作: {improvement['action']['change']}")
                print("  需要人工审核，已跳过")
                skipped_fixes.append(improvement)

        # 4. 生成修复报告
        fix_report = {
            "timestamp": datetime.now().isoformat(),
            "analysis_report": report,
            "applied_fixes": applied_fixes,
            "skipped_fixes": skipped_fixes,
            "summary": {
                "total_improvements": len(report["improvements"]),
                "applied": len(applied_fixes),
                "skipped": len(skipped_fixes),
                "success": sum(1 for f in applied_fixes if f["success"]),
                "failed": sum(1 for f in applied_fixes if not f["success"]),
            }
        }

        # 保存报告
        fix_report_path = FIX_DIR / f"fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(fix_report_path, "w", encoding="utf-8") as f:
            json.dump(fix_report, f, ensure_ascii=False, indent=2)

        print(f"\n修复报告已保存: {fix_report_path}")
        return fix_report

    def _apply_fix(self, improvement: Dict) -> Dict:
        """应用单个修复"""
        print(f"\n应用修复: {improvement['description']}")

        action = improvement["action"]
        fix_result = {
            "improvement": improvement,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": None,
            "details": {}
        }

        try:
            if action["type"] == "config_change":
                result = self._apply_config_change(action, improvement)
            elif action["type"] == "agent_action":
                result = self._apply_agent_action(action, improvement)
            elif action["type"] == "code_change":
                result = self._suggest_code_change(action, improvement)
            else:
                result = {"success": False, "error": f"Unknown action type: {action['type']}"}

            fix_result.update(result)

        except Exception as e:
            fix_result["error"] = str(e)
            print(f"  ✗ 失败: {e}")

        # 记录到日志
        with open(FIX_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(fix_result, ensure_ascii=False) + "\n")

        return fix_result

    def _apply_config_change(self, action: Dict, improvement: Dict) -> Dict:
        """应用配置变更"""
        target = action["target"]
        change = action["change"]

        # 加载当前配置
        config = self._load_agent_config()

        if target == "timeout":
            # 增加超时时间
            old_timeout = config.get("timeout", 30)
            new_timeout = int(old_timeout * 1.5)  # 增加 50%
            config["timeout"] = new_timeout

            print(f"  timeout: {old_timeout}s → {new_timeout}s")

            self._save_agent_config(config)
            return {
                "success": True,
                "details": {
                    "old_value": old_timeout,
                    "new_value": new_timeout,
                    "change": change
                }
            }

        elif target == "request_rate":
            # 降低请求频率
            old_delay = config.get("request_delay", 0)
            new_delay = max(old_delay, 1.5)  # 至少 1.5 秒延迟
            config["request_delay"] = new_delay

            print(f"  request_delay: {old_delay}s → {new_delay}s")

            self._save_agent_config(config)
            return {
                "success": True,
                "details": {
                    "old_value": old_delay,
                    "new_value": new_delay,
                    "change": change
                }
            }

        else:
            return {"success": False, "error": f"Unknown config target: {target}"}

    def _apply_agent_action(self, action: Dict, improvement: Dict) -> Dict:
        """应用 Agent 操作"""
        agent_id = action["target"]
        change = action["change"]

        if "降低优先级" in change:
            # 降低 Agent 优先级
            config = self._load_agent_config()
            agent_config = config.get("agents", {}).get(agent_id, {})
            old_priority = agent_config.get("priority", 1.0)
            new_priority = old_priority * 0.5  # 降低 50%

            if "agents" not in config:
                config["agents"] = {}
            if agent_id not in config["agents"]:
                config["agents"][agent_id] = {}

            config["agents"][agent_id]["priority"] = new_priority

            print(f"  {agent_id} priority: {old_priority} → {new_priority}")

            self._save_agent_config(config)
            return {
                "success": True,
                "details": {
                    "agent_id": agent_id,
                    "old_priority": old_priority,
                    "new_priority": new_priority,
                    "change": change
                }
            }

        elif "重启" in change:
            # 触发 Agent 重启（这里只是标记，实际重启需要外部系统执行）
            print(f"  标记 {agent_id} 需要重启")
            return {
                "success": True,
                "details": {
                    "agent_id": agent_id,
                    "action": "restart_required",
                    "change": change
                }
            }

        else:
            return {"success": False, "error": f"Unknown agent action: {change}"}

    def _suggest_code_change(self, action: Dict, improvement: Dict) -> Dict:
        """建议代码变更（不自动应用）"""
        target = action["target"]
        change = action["change"]

        print(f"  [代码变更建议] {target}: {change}")
        print(f"  需要人工实现，已记录到修复日志")

        return {
            "success": True,
            "details": {
                "target": target,
                "change": change,
                "note": "需要人工实现代码变更"
            }
        }

    def _load_agent_config(self) -> Dict:
        """加载 Agent 配置"""
        if AGENT_CONFIG.exists():
            with open(AGENT_CONFIG, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_agent_config(self, config: Dict):
        """保存 Agent 配置"""
        with open(AGENT_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)


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

    print("=== Agent Auto-Fixer ===\n")
    print(f"自动应用: {'是' if auto_apply else '否（需要确认）'}")
    print(f"分析周期: {days} 天")
    print(f"最少出现: {min_occurrences} 次\n")

    fixer = AgentAutoFixer(auto_apply=auto_apply)
    report = fixer.analyze_and_fix(days=days, min_occurrences=min_occurrences)

    if report.get("status") == "no_improvements":
        print("\n✓ 系统运行正常，无需修复")
        return

    summary = report["summary"]
    print(f"\n=== 修复摘要 ===")
    print(f"总改进建议: {summary['total_improvements']}")
    print(f"已应用: {summary['applied']} (成功 {summary['success']}, 失败 {summary['failed']})")
    print(f"已跳过: {summary['skipped']}")


if __name__ == "__main__":
    main()
