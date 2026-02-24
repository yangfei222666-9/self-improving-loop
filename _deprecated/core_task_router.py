"""
AIOS Task Router - 任务路由引擎

负责分析任务类型、匹配 Agent、决策是否创建新 Agent
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TaskRouter:
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        self.config_dir = Path(config_dir)

        self.rules_file = self.config_dir / "task_rules.json"
        self.rules: Dict = {}

        self._load_rules()

    def _load_rules(self):
        """加载任务分类规则"""
        if self.rules_file.exists():
            with open(self.rules_file, "r", encoding="utf-8") as f:
                self.rules = json.load(f)

    def analyze_task(self, message: str) -> Dict:
        """
        分析任务类型和复杂度

        Args:
            message: 用户消息

        Returns:
            {
                'task_type': str,  # code/analysis/monitor/research/design
                'complexity': str,  # high/medium/low
                'confidence': float,  # 0.0-1.0
                'keywords_matched': List[str],
                'recommended_template': str,
                'recommended_model': str
            }
        """
        message_lower = message.lower()

        # 匹配任务类型
        task_types = self.rules.get("task_types", {})
        type_scores = {}

        for task_type, config in task_types.items():
            keywords = config.get("keywords", [])
            matched = []

            for keyword in keywords:
                if keyword.lower() in message_lower:
                    matched.append(keyword)

            if matched:
                # 计算匹配分数（匹配关键词数量 / 总关键词数量）
                score = len(matched) / len(keywords) if keywords else 0
                type_scores[task_type] = {
                    "score": score,
                    "matched": matched,
                    "config": config,
                }

        # 选择得分最高的类型
        if not type_scores:
            # 默认为 research（信息查询）
            return {
                "task_type": "research",
                "complexity": "low",
                "confidence": 0.3,
                "keywords_matched": [],
                "recommended_template": "researcher",
                "recommended_model": "claude-sonnet-4-5",
            }

        best_type = max(type_scores.items(), key=lambda x: x[1]["score"])
        task_type = best_type[0]
        type_info = best_type[1]

        # 分析复杂度
        complexity = self._analyze_complexity(message)

        # 计算置信度
        confidence = min(type_info["score"] * 2, 1.0)  # 归一化到 0-1

        config = type_info["config"]

        return {
            "task_type": task_type,
            "complexity": complexity,
            "confidence": confidence,
            "keywords_matched": type_info["matched"],
            "recommended_template": config.get("agent_template"),
            "recommended_model": config.get("model"),
            "priority": config.get("priority", "medium"),
        }

    def _analyze_complexity(self, message: str) -> str:
        """
        分析任务复杂度

        Returns:
            'high' | 'medium' | 'low'
        """
        message_lower = message.lower()
        complexity_indicators = self.rules.get("complexity_indicators", {})

        # 检查高复杂度指标
        high_indicators = complexity_indicators.get("high", [])
        for indicator in high_indicators:
            if indicator.lower() in message_lower:
                return "high"

        # 检查低复杂度指标
        low_indicators = complexity_indicators.get("low", [])
        for indicator in low_indicators:
            if indicator.lower() in message_lower:
                return "low"

        # 默认中等复杂度
        return "medium"

    def match_agent(
        self, task_analysis: Dict, available_agents: List[Dict]
    ) -> Optional[str]:
        """
        匹配合适的 Agent

        Args:
            task_analysis: analyze_task 返回的结果
            available_agents: 可用 Agent 列表

        Returns:
            匹配的 Agent ID，如果没有合适的返回 None
        """
        recommended_template = task_analysis.get("recommended_template")

        # 筛选相同模板的 Agent
        matching_agents = [
            a
            for a in available_agents
            if a["template"] == recommended_template and a["status"] == "active"
        ]

        if not matching_agents:
            return None

        # 选择最空闲的 Agent（最近最少使用）
        def get_last_active(agent):
            last_active = agent["stats"].get("last_active")
            if not last_active:
                return 0  # 从未使用过，优先选择
            return last_active

        best_agent = min(matching_agents, key=get_last_active)
        return best_agent["id"]

    def should_create_new(
        self, task_analysis: Dict, available_agents: List[Dict]
    ) -> Tuple[bool, str]:
        """
        判断是否需要创建新 Agent

        Args:
            task_analysis: analyze_task 返回的结果
            available_agents: 可用 Agent 列表

        Returns:
            (should_create: bool, reason: str)
        """
        auto_create_rules = self.rules.get("auto_create_rules", {})

        if not auto_create_rules.get("enabled", True):
            return False, "Auto-create disabled"

        recommended_template = task_analysis.get("recommended_template")

        # 统计该模板的 Agent 数量
        template_agents = [
            a
            for a in available_agents
            if a["template"] == recommended_template and a["status"] == "active"
        ]

        max_per_type = auto_create_rules.get("max_agents_per_type", 3)

        if len(template_agents) >= max_per_type:
            return False, f"Max agents per type reached ({max_per_type})"

        # 如果没有该类型的 Agent，创建第一个
        if not template_agents:
            return True, "No agent of this type exists"

        # 检查现有 Agent 是否繁忙
        threshold = auto_create_rules.get("create_threshold", {})
        busy_rate_threshold = threshold.get("agent_busy_rate", 0.8)

        # 简化判断：如果所有 Agent 最近都活跃，认为繁忙
        # （实际应该检查任务队列长度，这里先简化）

        return False, "Existing agents available"

    def route_task(self, message: str, available_agents: List[Dict]) -> Dict:
        """
        完整的任务路由流程

        Args:
            message: 用户消息
            available_agents: 可用 Agent 列表

        Returns:
            {
                'action': 'assign' | 'create',
                'agent_id': str (if action='assign'),
                'template': str (if action='create'),
                'task_analysis': Dict,
                'reason': str
            }
        """
        # 1. 分析任务
        task_analysis = self.analyze_task(message)

        # 2. 尝试匹配现有 Agent
        matched_agent = self.match_agent(task_analysis, available_agents)

        if matched_agent:
            return {
                "action": "assign",
                "agent_id": matched_agent,
                "task_analysis": task_analysis,
                "reason": f"Matched existing agent: {matched_agent}",
            }

        # 3. 判断是否创建新 Agent
        should_create, reason = self.should_create_new(task_analysis, available_agents)

        if should_create:
            return {
                "action": "create",
                "template": task_analysis["recommended_template"],
                "task_analysis": task_analysis,
                "reason": reason,
            }

        # 4. 无法路由（不应该发生，因为会创建第一个 Agent）
        return {"action": "none", "task_analysis": task_analysis, "reason": reason}


if __name__ == "__main__":
    # 测试
    router = TaskRouter()

    test_messages = [
        "帮我写一个 Python 爬虫",
        "分析一下最近的系统日志",
        "检查服务器状态",
        "搜索一下 React 最新版本",
        "设计一个微服务架构",
    ]

    for msg in test_messages:
        analysis = router.analyze_task(msg)
        print(f"\n消息: {msg}")
        print(f"类型: {analysis['task_type']}")
        print(f"复杂度: {analysis['complexity']}")
        print(f"置信度: {analysis['confidence']:.2f}")
        print(f"推荐模板: {analysis['recommended_template']}")
        print(f"匹配关键词: {', '.join(analysis['keywords_matched'])}")
