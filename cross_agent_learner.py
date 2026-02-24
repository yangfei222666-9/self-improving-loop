"""
Cross-Agent Learner - 跨 Agent 知识共享

核心能力：
1. 从高成功率 Agent 提取最佳实践
2. 将教训传播给同类型 Agent
3. 维护共享知识库
4. 知识冲突检测和解决

知识流向：
  Agent A 成功经验 → 共享知识库 → Agent B 吸收 → Agent B 改进
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


class CrossAgentLearner:
    """跨 Agent 知识共享引擎"""

    MIN_SUCCESS_RATE = 0.7   # 最低成功率才提取经验
    MIN_TASKS = 5            # 最少任务数才提取经验

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path.home() / ".openclaw" / "workspace" / "aios" / "agent_system" / "data"
        self.data_dir = Path(data_dir)
        self.learning_dir = self.data_dir / "learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)

        self.knowledge_file = self.learning_dir / "shared_knowledge.json"
        self.transfer_log = self.learning_dir / "knowledge_transfers.jsonl"

    def extract_best_practices(self, agent_stats: Dict, agent_config: Dict) -> List[Dict]:
        """
        从高成功率 Agent 提取最佳实践

        Args:
            agent_stats: Agent 统计数据 (from TraceAnalyzer.get_agent_stats)
            agent_config: Agent 配置

        Returns:
            最佳实践列表
        """
        success_rate = agent_stats.get("success_rate", 0)
        total_tasks = agent_stats.get("total_tasks", 0)

        if success_rate < self.MIN_SUCCESS_RATE or total_tasks < self.MIN_TASKS:
            return []

        practices = []
        agent_id = agent_stats["agent_id"]
        template = agent_config.get("template", "unknown")

        # 提取配置特征
        thinking = agent_config.get("thinking", "off")
        model = agent_config.get("model", "unknown")
        tools = agent_config.get("tools", {})

        practices.append({
            "source_agent": agent_id,
            "template": template,
            "practice_type": "config",
            "content": {
                "thinking": thinking,
                "model": model,
                "tools": tools
            },
            "success_rate": success_rate,
            "sample_size": total_tasks,
            "extracted_at": datetime.now().isoformat()
        })

        # 提取常用工具组合
        common_tools = agent_stats.get("most_common_tools", [])
        if common_tools:
            practices.append({
                "source_agent": agent_id,
                "template": template,
                "practice_type": "tool_combo",
                "content": {"tools": common_tools},
                "success_rate": success_rate,
                "sample_size": total_tasks,
                "extracted_at": datetime.now().isoformat()
            })

        # 提取 prompt 中的自进化规则（如果有）
        prompt = agent_config.get("system_prompt", "")
        if "自进化规则" in prompt:
            # 提取自进化规则部分
            rules_section = prompt.split("自进化规则")[1] if "自进化规则" in prompt else ""
            if rules_section:
                practices.append({
                    "source_agent": agent_id,
                    "template": template,
                    "practice_type": "evolved_rules",
                    "content": {"rules": rules_section.strip()[:500]},
                    "success_rate": success_rate,
                    "sample_size": total_tasks,
                    "extracted_at": datetime.now().isoformat()
                })

        return practices

    def build_knowledge_base(self, all_practices: List[Dict]) -> Dict:
        """
        构建共享知识库

        Args:
            all_practices: 所有 Agent 的最佳实践

        Returns:
            按模板类型组织的知识库
        """
        knowledge = self._load_knowledge()

        for practice in all_practices:
            template = practice["template"]
            practice_type = practice["practice_type"]

            if template not in knowledge:
                knowledge[template] = {
                    "best_configs": [],
                    "tool_combos": [],
                    "evolved_rules": [],
                    "last_updated": None
                }

            # 按类型存储
            if practice_type == "config":
                self._update_best_config(knowledge[template], practice)
            elif practice_type == "tool_combo":
                self._update_tool_combo(knowledge[template], practice)
            elif practice_type == "evolved_rules":
                self._update_evolved_rules(knowledge[template], practice)

            knowledge[template]["last_updated"] = datetime.now().isoformat()

        self._save_knowledge(knowledge)
        return knowledge

    def _update_best_config(self, template_knowledge: Dict, practice: Dict):
        """更新最佳配置"""
        configs = template_knowledge["best_configs"]
        # 保留成功率最高的 3 个配置
        configs.append({
            "config": practice["content"],
            "success_rate": practice["success_rate"],
            "source": practice["source_agent"],
            "sample_size": practice["sample_size"]
        })
        configs.sort(key=lambda c: c["success_rate"], reverse=True)
        template_knowledge["best_configs"] = configs[:3]

    def _update_tool_combo(self, template_knowledge: Dict, practice: Dict):
        """更新工具组合"""
        combos = template_knowledge["tool_combos"]
        new_combo = practice["content"]["tools"]
        # 去重
        existing = [c["tools"] for c in combos]
        if new_combo not in existing:
            combos.append({
                "tools": new_combo,
                "success_rate": practice["success_rate"],
                "source": practice["source_agent"]
            })
        template_knowledge["tool_combos"] = combos[:5]

    def _update_evolved_rules(self, template_knowledge: Dict, practice: Dict):
        """更新进化规则"""
        rules = template_knowledge["evolved_rules"]
        rules.append({
            "rules": practice["content"]["rules"],
            "success_rate": practice["success_rate"],
            "source": practice["source_agent"]
        })
        # 保留成功率最高的
        rules.sort(key=lambda r: r["success_rate"], reverse=True)
        template_knowledge["evolved_rules"] = rules[:3]

    def transfer_knowledge(
        self,
        target_agent_id: str,
        target_config: Dict,
        agent_manager
    ) -> Dict:
        """
        将知识传播给目标 Agent

        Args:
            target_agent_id: 目标 Agent ID
            target_config: 目标 Agent 配置
            agent_manager: AgentManager 实例

        Returns:
            传播结果
        """
        template = target_config.get("template", "unknown")
        knowledge = self._load_knowledge()

        if template not in knowledge:
            return {"status": "no_knowledge", "message": f"无 {template} 类型的共享知识"}

        template_knowledge = knowledge[template]
        changes = {}

        # 1. 如果目标 Agent 成功率低，参考最佳配置
        target_stats = target_config.get("stats", {})
        target_success_rate = target_stats.get("success_rate", 0)
        target_total = target_stats.get("tasks_completed", 0) + target_stats.get("tasks_failed", 0)

        if target_total >= 5 and target_success_rate < 0.5:
            best_configs = template_knowledge.get("best_configs", [])
            if best_configs:
                best = best_configs[0]
                # 只调整 thinking level（最安全的改动）
                if best["config"].get("thinking") != target_config.get("thinking"):
                    changes["thinking"] = best["config"]["thinking"]

        # 2. 传播进化规则
        evolved_rules = template_knowledge.get("evolved_rules", [])
        if evolved_rules:
            best_rules = evolved_rules[0]
            current_prompt = target_config.get("system_prompt", "")
            if "自进化规则" not in current_prompt and best_rules["rules"]:
                rules_text = best_rules["rules"]
                # 只追加，不修改
                changes["system_prompt"] = current_prompt + f"\n\n## 共享知识（来自 {best_rules['source']}）\n{rules_text}"

        if not changes:
            return {"status": "no_changes", "message": "目标 Agent 无需调整"}

        # 应用变更
        agent_manager._update_agent(target_agent_id, changes)

        # 记录传播日志
        transfer = {
            "timestamp": int(time.time()),
            "target_agent": target_agent_id,
            "template": template,
            "changes": list(changes.keys()),
            "source_knowledge": template
        }
        with open(self.transfer_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(transfer, ensure_ascii=False) + "\n")

        return {
            "status": "transferred",
            "changes": list(changes.keys()),
            "message": f"已将 {len(changes)} 项知识传播给 {target_agent_id}"
        }

    def get_knowledge_summary(self) -> Dict:
        """获取知识库摘要"""
        knowledge = self._load_knowledge()
        summary = {}
        for template, data in knowledge.items():
            summary[template] = {
                "best_configs": len(data.get("best_configs", [])),
                "tool_combos": len(data.get("tool_combos", [])),
                "evolved_rules": len(data.get("evolved_rules", [])),
                "last_updated": data.get("last_updated")
            }
        return summary

    def _load_knowledge(self) -> Dict:
        """加载知识库"""
        if self.knowledge_file.exists():
            with open(self.knowledge_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_knowledge(self, knowledge: Dict):
        """保存知识库"""
        with open(self.knowledge_file, "w", encoding="utf-8") as f:
            json.dump(knowledge, f, ensure_ascii=False, indent=2)
