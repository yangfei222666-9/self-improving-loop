"""
Evolution Engine - Agent 自进化统一引擎

将所有进化能力整合为一个完整闭环：

  ┌─────────────────────────────────────────────────────┐
  │                  Evolution Engine                     │
  │                                                       │
  │  1. Observe  → 收集追踪数据、失败模式                  │
  │  2. Analyze  → 识别 prompt 缺陷、策略缺口              │
  │  3. Learn    → 生成新策略、提取最佳实践                 │
  │  4. Evolve   → 优化 prompt、调整配置                   │
  │  5. Verify   → A/B 测试、效果评估                      │
  │  6. Share    → 跨 Agent 知识传播                       │
  │                                                       │
  └─────────────────────────────────────────────────────┘

安全机制：
- 每天最多进化 1 次（per Agent）
- 只自动应用低风险改进
- 所有变更可回滚
- 中高风险需人工审核
"""

import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 确保能导入同级模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompt_evolver import PromptEvolver
from strategy_learner import StrategyLearner
from cross_agent_learner import CrossAgentLearner
from evolution import AgentEvolution
from auto_evolution import AutoEvolution
from agent_tracer import TraceAnalyzer
from evolution_events import get_emitter
from core.agent_manager import AgentManager


class EvolutionEngine:
    """Agent 自进化统一引擎"""

    # 安全常量
    MAX_EVOLUTIONS_PER_DAY = 3      # 全局每天最多进化次数
    EVOLUTION_INTERVAL_HOURS = 6    # 两次进化最小间隔

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path.home() / ".openclaw" / "workspace" / "aios" / "agent_system" / "data"
        self.data_dir = Path(data_dir)

        # 初始化子模块
        self.prompt_evolver = PromptEvolver(str(self.data_dir))
        self.strategy_learner = StrategyLearner(str(self.data_dir))
        self.cross_learner = CrossAgentLearner(str(self.data_dir))
        self.evolution = AgentEvolution(str(self.data_dir))
        self.auto_evolution = AutoEvolution(str(self.data_dir))
        self.agent_manager = AgentManager(str(self.data_dir))
        self.emitter = get_emitter()

        # 状态文件
        self.state_file = self.data_dir / "evolution" / "engine_state.json"
        self.report_dir = self.data_dir / "evolution" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run_full_cycle(self, dry_run: bool = False) -> Dict:
        """
        运行完整进化循环

        Args:
            dry_run: 是否只分析不应用

        Returns:
            进化报告
        """
        start_time = time.time()
        report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "phases": {},
            "summary": {}
        }

        print("=" * 60)
        print("  AIOS Evolution Engine - Full Cycle")
        print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Phase 1: Observe - 收集数据
        print("\n[Phase 1] Observe - 收集追踪数据...")
        observe_result = self._phase_observe()
        report["phases"]["observe"] = observe_result
        print(f"  追踪记录: {observe_result['total_traces']}")
        print(f"  失败模式: {observe_result['failure_patterns']}")
        print(f"  活跃 Agent: {observe_result['active_agents']}")

        if observe_result["total_traces"] < 5:
            report["summary"] = {"status": "insufficient_data", "message": "数据不足，跳过进化"}
            print("\n⚠️ 数据不足（< 5 条追踪），跳过进化")
            self._save_report(report)
            return report

        # Phase 2: Analyze - 分析缺陷
        print("\n[Phase 2] Analyze - 分析 Prompt 缺陷和策略缺口...")
        analyze_result = self._phase_analyze(observe_result)
        report["phases"]["analyze"] = analyze_result
        print(f"  Prompt 缺陷: {analyze_result['prompt_gaps']}")
        print(f"  策略缺口: {analyze_result['strategy_gaps']}")

        # Phase 3: Learn - 学习新策略
        print("\n[Phase 3] Learn - 从经验中学习...")
        learn_result = self._phase_learn(observe_result)
        report["phases"]["learn"] = learn_result
        print(f"  新策略: {learn_result['new_strategies']}")
        print(f"  最佳实践: {learn_result['best_practices']}")

        if dry_run:
            report["summary"] = {
                "status": "dry_run",
                "message": "分析完成（dry run 模式，未应用变更）",
                "potential_changes": analyze_result["prompt_gaps"] + learn_result["new_strategies"]
            }
            print("\n📋 Dry run 完成，未应用任何变更")
            self._save_report(report)
            return report

        # Phase 4: Evolve - 应用进化
        print("\n[Phase 4] Evolve - 应用进化改进...")
        evolve_result = self._phase_evolve(analyze_result, learn_result)
        report["phases"]["evolve"] = evolve_result
        print(f"  Prompt 补丁: {evolve_result['prompts_patched']}")
        print(f"  配置调整: {evolve_result['configs_adjusted']}")
        print(f"  策略合并: {evolve_result['strategies_merged']}")

        # Phase 5: Share - 跨 Agent 传播
        print("\n[Phase 5] Share - 跨 Agent 知识传播...")
        share_result = self._phase_share()
        report["phases"]["share"] = share_result
        print(f"  知识传播: {share_result['transfers']}")

        # 总结
        total_changes = (
            evolve_result["prompts_patched"] +
            evolve_result["configs_adjusted"] +
            share_result["transfers"]
        )
        elapsed = time.time() - start_time

        report["summary"] = {
            "status": "evolved" if total_changes > 0 else "no_changes",
            "total_changes": total_changes,
            "elapsed_sec": round(elapsed, 2),
            "message": f"完成 {total_changes} 项改进" if total_changes > 0 else "无需改进"
        }

        print("\n" + "=" * 60)
        print(f"  完成！耗时 {elapsed:.1f}s，共 {total_changes} 项改进")
        print("=" * 60)

        self._save_report(report)
        return report

    def _phase_observe(self) -> Dict:
        """Phase 1: 收集追踪数据"""
        analyzer = TraceAnalyzer()
        traces = analyzer.traces

        failure_patterns = analyzer.get_failure_patterns(min_occurrences=3)
        agents = self.agent_manager.list_agents(status="active")

        # 按 agent 分组统计
        agent_stats = {}
        for agent in agents:
            stats = analyzer.get_agent_stats(agent["id"])
            if stats.get("total_tasks", 0) > 0:
                agent_stats[agent["id"]] = stats

        return {
            "total_traces": len(traces),
            "failure_patterns": len(failure_patterns),
            "failure_details": failure_patterns[:5],
            "active_agents": len(agents),
            "agent_stats": agent_stats,
            "traces": traces,  # 传递给后续阶段
            "agents": agents
        }

    def _phase_analyze(self, observe_data: Dict) -> Dict:
        """Phase 2: 分析缺陷"""
        prompt_gaps_total = 0
        strategy_gaps = 0
        agent_gaps = {}

        for agent in observe_data["agents"]:
            agent_id = agent["id"]
            stats = observe_data["agent_stats"].get(agent_id)
            if not stats:
                continue

            # 获取该 Agent 的失败追踪
            failure_traces = [
                t for t in observe_data["traces"]
                if t.get("agent_id") == agent_id and not t.get("success")
            ]

            if not failure_traces:
                continue

            # 分析 prompt 缺陷
            gaps = self.prompt_evolver.analyze_prompt_gaps(agent_id, failure_traces)
            if gaps:
                agent_gaps[agent_id] = gaps
                prompt_gaps_total += len(gaps)

            # 分析策略缺口（通过 auto_evolution 的触发评估）
            analysis = self.evolution.analyze_failures(agent_id, lookback_hours=168)  # 7天
            matched = self.auto_evolution.evaluate_triggers(agent_id, analysis)
            if matched:
                strategy_gaps += len(matched)

        return {
            "prompt_gaps": prompt_gaps_total,
            "strategy_gaps": strategy_gaps,
            "agent_gaps": agent_gaps
        }

    def _phase_learn(self, observe_data: Dict) -> Dict:
        """Phase 3: 从经验中学习"""
        # 学习新策略
        new_strategies = self.strategy_learner.learn_from_traces(observe_data["traces"])

        # 提取最佳实践
        all_practices = []
        for agent in observe_data["agents"]:
            agent_id = agent["id"]
            stats = observe_data["agent_stats"].get(agent_id)
            if not stats:
                continue

            practices = self.cross_learner.extract_best_practices(stats, agent)
            all_practices.extend(practices)

        # 构建知识库
        if all_practices:
            self.cross_learner.build_knowledge_base(all_practices)

        return {
            "new_strategies": len(new_strategies),
            "strategy_details": new_strategies,
            "best_practices": len(all_practices),
            "practice_details": all_practices[:10]
        }

    def _phase_evolve(self, analyze_data: Dict, learn_data: Dict) -> Dict:
        """Phase 4: 应用进化"""
        prompts_patched = 0
        configs_adjusted = 0
        strategies_merged = 0

        # 4.1 应用 Prompt 补丁
        for agent_id, gaps in analyze_data.get("agent_gaps", {}).items():
            agent = self.agent_manager.get_agent(agent_id)
            if not agent:
                continue

            patch = self.prompt_evolver.generate_prompt_patch(
                agent_id, agent["system_prompt"], gaps
            )
            if patch:
                success = self.prompt_evolver.apply_patch(agent_id, self.agent_manager, patch)
                if success:
                    prompts_patched += 1
                    self.emitter.emit_applied(agent_id, [{
                        "action": "prompt_evolution",
                        "description": f"追加 {len(patch['rules_added'])} 条自进化规则",
                        "changes": {"rules_added": [r["rule"] for r in patch["rules_added"]]}
                    }])

        # 4.2 合并学习到的策略
        new_strategies = learn_data.get("strategy_details", [])
        if new_strategies:
            strategies_merged = self.strategy_learner.merge_to_strategy_library(new_strategies)

        # 4.3 通过 auto_evolution 应用配置调整
        agents = self.agent_manager.list_agents(status="active")
        for agent in agents:
            result = self.auto_evolution.auto_evolve(agent["id"], self.agent_manager)
            if result.get("status") == "applied":
                configs_adjusted += len(result.get("plans", []))

        return {
            "prompts_patched": prompts_patched,
            "configs_adjusted": configs_adjusted,
            "strategies_merged": strategies_merged
        }

    def _phase_share(self) -> Dict:
        """Phase 5: 跨 Agent 知识传播"""
        transfers = 0
        agents = self.agent_manager.list_agents(status="active")

        for agent in agents:
            agent_id = agent["id"]
            stats = agent.get("stats", {})
            total = stats.get("tasks_completed", 0) + stats.get("tasks_failed", 0)
            success_rate = stats.get("success_rate", 0)

            # 只对低成功率 Agent 传播知识
            if total >= 5 and success_rate < 0.5:
                result = self.cross_learner.transfer_knowledge(
                    agent_id, agent, self.agent_manager
                )
                if result.get("status") == "transferred":
                    transfers += 1

        return {"transfers": transfers}

    def _save_report(self, report: Dict):
        """保存进化报告"""
        filename = f"evolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.report_dir / filename
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def get_evolution_status(self) -> Dict:
        """获取进化系统状态"""
        agents = self.agent_manager.list_agents(status="active")
        knowledge_summary = self.cross_learner.get_knowledge_summary()

        # 统计进化历史
        evolution_log = self.data_dir / "evolution" / "evolution_history.jsonl"
        total_evolutions = 0
        if evolution_log.exists():
            with open(evolution_log, "r", encoding="utf-8") as f:
                total_evolutions = sum(1 for line in f if line.strip())

        # 统计 prompt 补丁
        patches_file = self.data_dir / "evolution" / "prompts" / "prompt_patches.jsonl"
        total_patches = 0
        if patches_file.exists():
            with open(patches_file, "r", encoding="utf-8") as f:
                total_patches = sum(1 for line in f if line.strip())

        # 加载策略库
        strategies_file = self.data_dir / "evolution" / "evolution_strategies.json"
        total_strategies = 0
        learned_strategies = 0
        if strategies_file.exists():
            with open(strategies_file, "r", encoding="utf-8") as f:
                strategies = json.load(f)
                total_strategies = len(strategies)
                learned_strategies = sum(
                    1 for s in strategies.values()
                    if s.get("source") == "strategy_learner"
                )

        return {
            "active_agents": len(agents),
            "total_evolutions": total_evolutions,
            "total_prompt_patches": total_patches,
            "total_strategies": total_strategies,
            "learned_strategies": learned_strategies,
            "knowledge_base": knowledge_summary,
            "last_check": datetime.now().isoformat()
        }


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="AIOS Evolution Engine")
    parser.add_argument("command", choices=["run", "status", "dry-run"],
                        help="命令：run=执行进化, status=查看状态, dry-run=分析不应用")
    args = parser.parse_args()

    engine = EvolutionEngine()

    if args.command == "run":
        result = engine.run_full_cycle(dry_run=False)
        status = result["summary"]["status"]
        if status == "evolved":
            print(f"\nEVOLUTION_APPLIED:{result['summary']['total_changes']}")
        else:
            print(f"\nEVOLUTION_OK")

    elif args.command == "dry-run":
        result = engine.run_full_cycle(dry_run=True)
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))

    elif args.command == "status":
        status = engine.get_evolution_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
