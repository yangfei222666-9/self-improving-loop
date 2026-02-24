"""
Prompt Evolver - Agent Prompt 自进化模块

核心能力：
1. 分析失败模式，识别 prompt 缺陷
2. 生成 prompt 补丁（追加规则/约束）
3. A/B 测试新旧 prompt
4. 自动回滚无效变更

安全机制：
- 只追加规则，不删除原有 prompt
- 每次最多追加 3 条规则
- 变更前保存快照，支持回滚
"""

import json
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter


class PromptEvolver:
    """Agent Prompt 自进化引擎"""

    MAX_RULES_PER_EVOLUTION = 3
    MIN_FAILURES_TO_TRIGGER = 3
    SNAPSHOT_KEEP = 10  # 保留最近 N 个快照

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path.home() / ".openclaw" / "workspace" / "aios" / "agent_system" / "data"
        self.data_dir = Path(data_dir)
        self.evolution_dir = self.data_dir / "evolution"
        self.prompt_dir = self.evolution_dir / "prompts"
        self.prompt_dir.mkdir(parents=True, exist_ok=True)

        self.snapshots_file = self.prompt_dir / "prompt_snapshots.jsonl"
        self.patches_file = self.prompt_dir / "prompt_patches.jsonl"

    def analyze_prompt_gaps(self, agent_id: str, failure_traces: List[Dict]) -> List[Dict]:
        """
        分析失败追踪，识别 prompt 中缺失的规则/约束

        Args:
            agent_id: Agent ID
            failure_traces: 失败的任务追踪列表

        Returns:
            识别出的 prompt 缺陷列表
        """
        if len(failure_traces) < self.MIN_FAILURES_TO_TRIGGER:
            return []

        gaps = []

        # 1. 错误模式聚类
        error_clusters = self._cluster_errors(failure_traces)

        for cluster_key, cluster in error_clusters.items():
            if len(cluster) < self.MIN_FAILURES_TO_TRIGGER:
                continue

            gap = self._identify_gap(cluster_key, cluster)
            if gap:
                gaps.append(gap)

        return gaps

    def _cluster_errors(self, traces: List[Dict]) -> Dict[str, List[Dict]]:
        """将错误按模式聚类"""
        clusters = {}
        for trace in traces:
            error = trace.get("error", "") or ""
            sig = self._error_signature(error)
            if sig not in clusters:
                clusters[sig] = []
            clusters[sig].append(trace)
        return clusters

    def _error_signature(self, error: str) -> str:
        """生成错误签名"""
        sig = re.sub(r'\d+', 'N', error)
        sig = re.sub(r'[A-Z]:\\[^\s]+', 'PATH', sig)
        sig = re.sub(r'/[^\s]+', 'PATH', sig)
        sig = re.sub(r'"[^"]*"', 'STR', sig)
        sig = re.sub(r"'[^']*'", 'STR', sig)
        return sig[:120]

    def _identify_gap(self, error_sig: str, traces: List[Dict]) -> Optional[Dict]:
        """识别单个错误模式对应的 prompt 缺陷"""
        sample_errors = [t.get("error", "") for t in traces[:5]]
        sample_tasks = [t.get("task", "") for t in traces[:5]]

        # 基于错误模式匹配规则模板
        rules = []

        # 超时类
        if any(kw in error_sig.lower() for kw in ["timeout", "timed out", "超时"]):
            rules.append({
                "type": "constraint",
                "rule": "对于复杂任务，先分解为子步骤再逐步执行，避免单步超时",
                "category": "timeout"
            })

        # 权限类
        if any(kw in error_sig.lower() for kw in ["permission", "denied", "权限", "access"]):
            rules.append({
                "type": "constraint",
                "rule": "执行系统命令前先检查权限，必要时使用提权方式",
                "category": "permission"
            })

        # 路径类
        if any(kw in error_sig.lower() for kw in ["not found", "no such file", "找不到", "path"]):
            rules.append({
                "type": "constraint",
                "rule": "操作文件前先验证路径存在，使用绝对路径避免歧义",
                "category": "path"
            })

        # 编码类
        if any(kw in error_sig.lower() for kw in ["encoding", "decode", "codec", "utf", "gbk", "编码"]):
            rules.append({
                "type": "constraint",
                "rule": "文件操作统一使用 UTF-8 编码，终端输出乱码不代表文件内容错误",
                "category": "encoding"
            })

        # API/网络类
        if any(kw in error_sig.lower() for kw in ["502", "503", "rate limit", "connection", "api"]):
            rules.append({
                "type": "constraint",
                "rule": "API 调用失败时自动重试（最多3次，指数退避），不要立即报错",
                "category": "api"
            })

        # 语法类
        if any(kw in error_sig.lower() for kw in ["syntax", "parse", "unexpected", "语法"]):
            rules.append({
                "type": "constraint",
                "rule": "生成代码后先做语法检查，确保可直接运行",
                "category": "syntax"
            })

        # PowerShell 特有
        if any(kw in error_sig.lower() for kw in ["powershell", "cmdlet", "&&"]):
            rules.append({
                "type": "constraint",
                "rule": "PowerShell 中用分号(;)连接命令，不用 &&；用 Get-ChildItem 不用 dir /b",
                "category": "powershell"
            })

        if not rules:
            # 通用规则：记录错误模式供人工审查
            rules.append({
                "type": "observation",
                "rule": f"重复错误模式: {error_sig[:80]}",
                "category": "unknown"
            })

        return {
            "error_signature": error_sig,
            "occurrences": len(traces),
            "sample_errors": sample_errors[:3],
            "sample_tasks": sample_tasks[:3],
            "suggested_rules": rules,
            "confidence": min(len(traces) / 10.0, 1.0)  # 出现越多越有信心
        }

    def generate_prompt_patch(
        self,
        agent_id: str,
        current_prompt: str,
        gaps: List[Dict]
    ) -> Optional[Dict]:
        """
        生成 prompt 补丁

        Args:
            agent_id: Agent ID
            current_prompt: 当前 system prompt
            gaps: 识别出的缺陷列表

        Returns:
            补丁信息，包含新增规则
        """
        if not gaps:
            return None

        # 按置信度排序，取 top N
        sorted_gaps = sorted(gaps, key=lambda g: g["confidence"], reverse=True)
        top_gaps = sorted_gaps[:self.MAX_RULES_PER_EVOLUTION]

        # 收集所有建议规则（只取 constraint 类型）
        new_rules = []
        for gap in top_gaps:
            for rule in gap["suggested_rules"]:
                if rule["type"] == "constraint" and rule["rule"] not in current_prompt:
                    new_rules.append(rule)

        if not new_rules:
            return None

        # 限制数量
        new_rules = new_rules[:self.MAX_RULES_PER_EVOLUTION]

        # 生成补丁文本
        patch_text = "\n\n## 自进化规则（自动生成）\n"
        for i, rule in enumerate(new_rules, 1):
            patch_text += f"- {rule['rule']}\n"

        return {
            "agent_id": agent_id,
            "timestamp": int(time.time()),
            "rules_added": new_rules,
            "patch_text": patch_text,
            "new_prompt": current_prompt + patch_text,
            "gaps_addressed": [g["error_signature"][:60] for g in top_gaps]
        }

    def save_snapshot(self, agent_id: str, prompt: str, reason: str = ""):
        """保存 prompt 快照（用于回滚）"""
        snapshot = {
            "agent_id": agent_id,
            "timestamp": int(time.time()),
            "prompt": prompt,
            "reason": reason
        }
        with open(self.snapshots_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

    def get_last_snapshot(self, agent_id: str) -> Optional[Dict]:
        """获取最近的 prompt 快照"""
        if not self.snapshots_file.exists():
            return None

        last = None
        with open(self.snapshots_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record["agent_id"] == agent_id:
                        last = record
                except (json.JSONDecodeError, KeyError):
                    continue
        return last

    def rollback_prompt(self, agent_id: str) -> Optional[str]:
        """回滚到上一个 prompt 快照"""
        snapshot = self.get_last_snapshot(agent_id)
        if snapshot:
            return snapshot["prompt"]
        return None

    def apply_patch(
        self,
        agent_id: str,
        agent_manager,
        patch: Dict
    ) -> bool:
        """
        应用 prompt 补丁

        Args:
            agent_id: Agent ID
            agent_manager: AgentManager 实例
            patch: generate_prompt_patch 的返回值

        Returns:
            是否成功
        """
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            return False

        # 保存快照
        self.save_snapshot(agent_id, agent["system_prompt"], reason="before_evolution")

        # 应用新 prompt
        agent_manager._update_agent(agent_id, {"system_prompt": patch["new_prompt"]})

        # 记录补丁
        patch_record = {
            **patch,
            "applied_at": datetime.now().isoformat(),
            "status": "applied"
        }
        with open(self.patches_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(patch_record, ensure_ascii=False) + "\n")

        return True

    def get_patch_history(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """获取 prompt 补丁历史"""
        if not self.patches_file.exists():
            return []

        patches = []
        with open(self.patches_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record["agent_id"] == agent_id:
                        patches.append(record)
                except (json.JSONDecodeError, KeyError):
                    continue

        patches.sort(key=lambda x: x["timestamp"], reverse=True)
        return patches[:limit]
