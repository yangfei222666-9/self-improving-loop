"""
Strategy Learner - 从经验中自动生成新进化策略

核心能力：
1. 分析成功/失败模式，提取规律
2. 自动生成新的进化策略
3. 策略效果评估和淘汰
4. 策略版本管理

学习闭环：
  执行 → 记录 → 分析 → 生成策略 → 验证 → 纳入策略库
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter, defaultdict


class StrategyLearner:
    """从经验中学习新进化策略"""

    MIN_SAMPLES = 5          # 最少样本数才生成策略
    MIN_CONFIDENCE = 0.6     # 最低置信度
    MAX_STRATEGIES = 20      # 策略库上限
    STRATEGY_TTL_DAYS = 30   # 策略有效期（天）

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path.home() / ".openclaw" / "workspace" / "aios" / "agent_system" / "data"
        self.data_dir = Path(data_dir)
        self.evolution_dir = self.data_dir / "evolution"
        self.evolution_dir.mkdir(parents=True, exist_ok=True)

        self.strategies_file = self.evolution_dir / "evolution_strategies.json"
        self.learned_file = self.evolution_dir / "learned_strategies.jsonl"
        self.strategy_scores_file = self.evolution_dir / "strategy_scores.json"

    def learn_from_traces(self, traces: List[Dict]) -> List[Dict]:
        """
        从任务追踪中学习新策略

        Args:
            traces: 任务追踪列表

        Returns:
            新生成的策略列表
        """
        if len(traces) < self.MIN_SAMPLES:
            return []

        new_strategies = []

        # 1. 分析成功模式 → 提取最佳实践
        success_patterns = self._analyze_success_patterns(traces)
        for pattern in success_patterns:
            strategy = self._pattern_to_strategy(pattern, "success")
            if strategy:
                new_strategies.append(strategy)

        # 2. 分析失败模式 → 生成防御策略
        failure_patterns = self._analyze_failure_patterns(traces)
        for pattern in failure_patterns:
            strategy = self._pattern_to_strategy(pattern, "failure")
            if strategy:
                new_strategies.append(strategy)

        # 3. 分析工具使用模式 → 优化工具配置
        tool_patterns = self._analyze_tool_patterns(traces)
        for pattern in tool_patterns:
            strategy = self._pattern_to_strategy(pattern, "tool")
            if strategy:
                new_strategies.append(strategy)

        # 去重
        new_strategies = self._deduplicate(new_strategies)

        # 记录学习结果
        for strategy in new_strategies:
            self._save_learned(strategy)

        return new_strategies

    def _analyze_success_patterns(self, traces: List[Dict]) -> List[Dict]:
        """分析成功任务的共同特征"""
        successes = [t for t in traces if t.get("success")]
        if len(successes) < self.MIN_SAMPLES:
            return []

        patterns = []

        # 按 agent 分组，找出高成功率 agent 的特征
        agent_stats = defaultdict(lambda: {"success": 0, "total": 0, "configs": []})
        for trace in traces:
            agent_id = trace.get("agent_id", "unknown")
            agent_stats[agent_id]["total"] += 1
            if trace.get("success"):
                agent_stats[agent_id]["success"] += 1
            agent_stats[agent_id]["configs"].append(trace.get("context", {}))

        for agent_id, stats in agent_stats.items():
            if stats["total"] < 3:
                continue
            success_rate = stats["success"] / stats["total"]
            if success_rate > 0.8:
                patterns.append({
                    "type": "high_success_agent",
                    "agent_id": agent_id,
                    "success_rate": success_rate,
                    "sample_size": stats["total"],
                    "confidence": min(stats["total"] / 10.0, 1.0)
                })

        # 分析成功任务的平均耗时
        durations = [t.get("duration_sec", 0) for t in successes if t.get("duration_sec")]
        if durations:
            avg_duration = sum(durations) / len(durations)
            fast_tasks = [t for t in successes if t.get("duration_sec", 0) < avg_duration * 0.5]
            if len(fast_tasks) >= 3:
                patterns.append({
                    "type": "fast_success",
                    "avg_duration": avg_duration,
                    "fast_count": len(fast_tasks),
                    "confidence": min(len(fast_tasks) / 10.0, 1.0)
                })

        return patterns

    def _analyze_failure_patterns(self, traces: List[Dict]) -> List[Dict]:
        """分析失败任务的共同特征"""
        failures = [t for t in traces if not t.get("success")]
        if len(failures) < self.MIN_SAMPLES:
            return []

        patterns = []

        # 按错误类型聚类
        error_types = Counter()
        error_contexts = defaultdict(list)
        for trace in failures:
            error = trace.get("error", "") or ""
            error_type = self._classify_error(error)
            error_types[error_type] += 1
            error_contexts[error_type].append({
                "agent_id": trace.get("agent_id"),
                "task": trace.get("task", "")[:100],
                "duration": trace.get("duration_sec", 0)
            })

        for error_type, count in error_types.items():
            if count >= self.MIN_SAMPLES:
                patterns.append({
                    "type": "recurring_error",
                    "error_type": error_type,
                    "count": count,
                    "contexts": error_contexts[error_type][:5],
                    "confidence": min(count / 10.0, 1.0)
                })

        # 检测连续失败（同一 agent 连续失败 3+ 次）
        agent_sequences = defaultdict(list)
        for trace in sorted(traces, key=lambda t: t.get("start_time", "")):
            agent_id = trace.get("agent_id", "unknown")
            agent_sequences[agent_id].append(trace.get("success", False))

        for agent_id, seq in agent_sequences.items():
            max_consecutive_failures = 0
            current = 0
            for s in seq:
                if not s:
                    current += 1
                    max_consecutive_failures = max(max_consecutive_failures, current)
                else:
                    current = 0

            if max_consecutive_failures >= 3:
                patterns.append({
                    "type": "consecutive_failures",
                    "agent_id": agent_id,
                    "max_streak": max_consecutive_failures,
                    "confidence": 0.8
                })

        return patterns

    def _analyze_tool_patterns(self, traces: List[Dict]) -> List[Dict]:
        """分析工具使用模式"""
        patterns = []

        # 统计工具使用和成功率的关系
        tool_success = defaultdict(lambda: {"used": 0, "success": 0})
        for trace in traces:
            tools_used = set()
            for tool_call in trace.get("tools_used", []):
                tools_used.add(tool_call.get("tool", "unknown"))

            for tool in tools_used:
                tool_success[tool]["used"] += 1
                if trace.get("success"):
                    tool_success[tool]["success"] += 1

        # 找出高成功率工具组合
        for tool, stats in tool_success.items():
            if stats["used"] < 3:
                continue
            success_rate = stats["success"] / stats["used"]
            if success_rate < 0.3:
                patterns.append({
                    "type": "low_tool_success",
                    "tool": tool,
                    "success_rate": success_rate,
                    "used_count": stats["used"],
                    "confidence": min(stats["used"] / 10.0, 1.0)
                })

        return patterns

    def _classify_error(self, error: str) -> str:
        """将错误分类"""
        error_lower = error.lower()
        if any(kw in error_lower for kw in ["timeout", "timed out", "超时"]):
            return "timeout"
        if any(kw in error_lower for kw in ["permission", "denied", "权限"]):
            return "permission"
        if any(kw in error_lower for kw in ["not found", "no such", "找不到"]):
            return "not_found"
        if any(kw in error_lower for kw in ["502", "503", "rate limit"]):
            return "api_error"
        if any(kw in error_lower for kw in ["syntax", "parse", "unexpected"]):
            return "syntax"
        if any(kw in error_lower for kw in ["memory", "oom", "内存"]):
            return "resource"
        return "other"

    def _pattern_to_strategy(self, pattern: Dict, source: str) -> Optional[Dict]:
        """将模式转换为进化策略"""
        if pattern.get("confidence", 0) < self.MIN_CONFIDENCE:
            return None

        pattern_type = pattern["type"]

        if pattern_type == "recurring_error":
            error_type = pattern["error_type"]
            action_map = {
                "timeout": ("increase_timeout", "low", True),
                "permission": ("adjust_permissions", "medium", False),
                "not_found": ("add_path_validation", "low", True),
                "api_error": ("add_retry", "low", True),
                "syntax": ("add_syntax_check", "low", True),
                "resource": ("reduce_complexity", "medium", False),
            }
            action, risk, auto = action_map.get(error_type, ("manual_review", "high", False))

            return {
                "name": f"learned_{error_type}_{int(time.time())}",
                "trigger": {"error_pattern": error_type, "count": f">={pattern['count']}"},
                "action": action,
                "risk": risk,
                "auto_apply": auto,
                "description": f"学习到的策略：{error_type} 错误出现 {pattern['count']} 次",
                "source": "strategy_learner",
                "learned_at": datetime.now().isoformat(),
                "confidence": pattern["confidence"],
                "sample_size": pattern["count"]
            }

        elif pattern_type == "consecutive_failures":
            return {
                "name": f"learned_consecutive_fail_{pattern['agent_id']}_{int(time.time())}",
                "trigger": {"consecutive_failures": f">={pattern['max_streak']}"},
                "action": "increase_thinking",
                "risk": "low",
                "auto_apply": True,
                "description": f"Agent {pattern['agent_id']} 连续失败 {pattern['max_streak']} 次，提升思考深度",
                "source": "strategy_learner",
                "learned_at": datetime.now().isoformat(),
                "confidence": pattern["confidence"],
                "sample_size": pattern["max_streak"]
            }

        elif pattern_type == "low_tool_success":
            return {
                "name": f"learned_tool_{pattern['tool']}_{int(time.time())}",
                "trigger": {"tool_failure_rate": f">{1 - pattern['success_rate']:.2f}", "tool": pattern["tool"]},
                "action": "adjust_tools",
                "risk": "medium",
                "auto_apply": False,
                "description": f"工具 {pattern['tool']} 成功率仅 {pattern['success_rate']:.1%}，需要调整",
                "source": "strategy_learner",
                "learned_at": datetime.now().isoformat(),
                "confidence": pattern["confidence"],
                "sample_size": pattern["used_count"]
            }

        return None

    def _deduplicate(self, strategies: List[Dict]) -> List[Dict]:
        """去重：相同 action + 相同 trigger 类型的只保留置信度最高的"""
        seen = {}
        for s in strategies:
            key = f"{s['action']}_{list(s['trigger'].keys())[0] if s['trigger'] else 'none'}"
            if key not in seen or s.get("confidence", 0) > seen[key].get("confidence", 0):
                seen[key] = s
        return list(seen.values())

    def _save_learned(self, strategy: Dict):
        """保存学习到的策略"""
        with open(self.learned_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(strategy, ensure_ascii=False) + "\n")

    def merge_to_strategy_library(self, new_strategies: List[Dict]) -> int:
        """
        将学习到的策略合并到策略库

        Args:
            new_strategies: 新策略列表

        Returns:
            实际合并的数量
        """
        # 加载现有策略库
        if self.strategies_file.exists():
            with open(self.strategies_file, "r", encoding="utf-8") as f:
                library = json.load(f)
        else:
            library = {}

        merged = 0
        for strategy in new_strategies:
            name = strategy["name"]
            # 检查上限
            if len(library) >= self.MAX_STRATEGIES:
                # 淘汰最旧的学习策略
                self._evict_oldest_learned(library)

            if name not in library:
                library[name] = {
                    "trigger": strategy["trigger"],
                    "action": strategy["action"],
                    "risk": strategy["risk"],
                    "auto_apply": strategy["auto_apply"],
                    "description": strategy["description"],
                    "source": strategy.get("source", "strategy_learner"),
                    "learned_at": strategy.get("learned_at"),
                    "confidence": strategy.get("confidence", 0.5)
                }
                merged += 1

        # 保存
        with open(self.strategies_file, "w", encoding="utf-8") as f:
            json.dump(library, f, ensure_ascii=False, indent=2)

        return merged

    def _evict_oldest_learned(self, library: Dict):
        """淘汰最旧的学习策略（保留手动策略）"""
        learned = {k: v for k, v in library.items() if v.get("source") == "strategy_learner"}
        if not learned:
            return

        oldest_key = min(learned.keys(), key=lambda k: learned[k].get("learned_at", ""))
        del library[oldest_key]

    def evaluate_strategy(self, strategy_name: str, recent_results: List[bool]) -> Dict:
        """
        评估策略效果

        Args:
            strategy_name: 策略名称
            recent_results: 最近应用后的结果列表 (True=成功, False=失败)

        Returns:
            评估结果
        """
        if not recent_results:
            return {"status": "no_data", "score": 0}

        success_rate = sum(recent_results) / len(recent_results)

        # 加载/更新评分
        scores = {}
        if self.strategy_scores_file.exists():
            with open(self.strategy_scores_file, "r", encoding="utf-8") as f:
                scores = json.load(f)

        scores[strategy_name] = {
            "success_rate": success_rate,
            "sample_size": len(recent_results),
            "last_evaluated": datetime.now().isoformat()
        }

        with open(self.strategy_scores_file, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)

        if success_rate >= 0.7:
            return {"status": "effective", "score": success_rate}
        elif success_rate >= 0.4:
            return {"status": "marginal", "score": success_rate}
        else:
            return {"status": "ineffective", "score": success_rate, "recommend": "remove"}
