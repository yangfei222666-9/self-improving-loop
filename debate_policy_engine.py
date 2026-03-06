"""
Debate Policy Engine - Phase 1 MVP
根据 Evolution Score + Hexagram 自动生成辩论配置

核心流程：
1. get_system_state() - 拉取当前系统状态
2. build_debate_policy(state) - 生成辩论策略
3. record_decision_audit() - 记录审计日志

公共符号说明：
- TaskMeta (dataclass) - 测试/统一入口，推荐使用
- _TaskMetaV2 (TypedDict) - 历史兼容结构，内部保留
- HexagramState (dataclass) - 卦象状态封装
- DebatePolicyEngine (class) - OOP 入口，推荐使用

破坏性变更（v3.5+）：
TaskMeta 公共符号语义已从 TypedDict 切换为 dataclass。
旧 TypedDict 结构已重命名为 _TaskMetaV2，仅供内部兼容使用。
"""

import hashlib
import json
import os
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TypedDict, Literal, Optional
from datetime import datetime

from phase3_types import GenerateRequest, GenerateResponse, DecisionResult, TokenUsage


# ============================================================
# OOP 入口：DebatePolicyEngine + 配套 dataclass
# ============================================================

@dataclass
class HexagramState:
    """卦象状态（OOP 入口用）"""
    hexagram: str
    evolution_score: float
    hexagram_id: int = 0
    confidence: float = 0.9

    def __post_init__(self):
        if self.hexagram_id == 0:
            self.hexagram_id = _parse_hexagram_id_static(self.hexagram)


@dataclass
class TaskMeta:
    """任务元数据（OOP 入口用）"""
    task_id: str
    risk_level: str          # low / medium / high
    content: str = ""
    task_type: str = "code_change"
    risk_keywords: list = field(default_factory=list)
    estimated_impact: str = "medium"


def _parse_hexagram_id_static(hexagram_str: str) -> int:
    """从卦象字符串解析卦序号（模块级，供 dataclass 使用）"""
    import re
    match = re.search(r"#(\d+)", hexagram_str)
    if match:
        return int(match.group(1))
    hexagram_map = {
        "坤卦": 2, "乾卦": 1, "大过卦": 28,
        "既济卦": 63, "未济卦": 64, "离卦": 30,
    }
    for name, hid in hexagram_map.items():
        if name in hexagram_str:
            return hid
    return 2


class DebatePolicyEngine:
    """
    OOP 入口：封装 Bull vs Bear 辩论 + 64卦调解 + 异常处理
    
    用法：
        engine = DebatePolicyEngine(llm_client=provider)
        result = engine.evaluate(task_meta=task, state=state)
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def evaluate(
        self,
        task_meta: TaskMeta,
        state: HexagramState,
    ) -> DecisionResult:
        """
        执行完整辩论流程，返回 DecisionResult
        
        Args:
            task_meta: 任务元数据
            state: 卦象状态
        
        Returns:
            DecisionResult
        """
        sys_state = {
            "evolution_score": state.evolution_score,
            "hexagram": state.hexagram,
            "hexagram_id": state.hexagram_id,
            "timestamp": datetime.now().isoformat(),
            "confidence": state.confidence,
        }

        policy = build_debate_policy(sys_state)
        policy["task_risk_level"] = task_meta.risk_level

        # 大过卦 + 高风险 → 硬门控
        if state.hexagram_id == 28 and task_meta.risk_level == "high":
            audit_id = record_decision_audit(
                task_id=task_meta.task_id,
                system_state=sys_state,
                debate_policy=policy,
                debate_result={"crisis_gate": True},
                final_decision="defer",
            )
            return DecisionResult(
                verdict="defer",
                reason="大过卦 + 高风险 → 强制人工审批",
                rounds_used=0,
                early_exit=True,
                confidence=0.0,
                requires_human_gate=True,
                audit_id=audit_id,
            )

        if self.llm_client is None:
            return DecisionResult(
                verdict="defer",
                reason="No LLM client configured",
                rounds_used=0,
                early_exit=True,
                confidence=0.0,
                requires_human_gate=True,
                audit_id="",
            )

        max_rounds = policy["max_rounds"]
        bull_weight = policy["bull_weight"]
        bear_weight = policy["bear_weight"]
        bull_args, bear_args = [], []

        for round_num in range(1, max_rounds + 1):
            # Bull
            bull_req = GenerateRequest(
                role="bull",
                prompt=f"任务：{task_meta.content}\n风险：{task_meta.risk_level}\n请生成支持论据（1-2句）",
                context={"round": round_num},
                trace_id=f"bull-r{round_num}",
            )
            try:
                bull_resp = self.llm_client.generate(bull_req)
            except Exception as e:
                return _defer(f"Bull 异常: {type(e).__name__}", round_num)

            if not bull_resp.ok or not bull_resp.text.strip():
                return _defer("Bull 空响应", round_num)
            bull_args.append(bull_resp.text.strip())

            # Bear
            bear_req = GenerateRequest(
                role="bear",
                prompt=f"任务：{task_meta.content}\n风险：{task_meta.risk_level}\nBull：{bull_resp.text}\n请识别风险（1-2句）",
                context={"round": round_num},
                trace_id=f"bear-r{round_num}",
            )
            try:
                bear_resp = self.llm_client.generate(bear_req)
            except Exception as e:
                return _defer(f"Bear 异常: {type(e).__name__}", round_num)

            if not bear_resp.ok or not bear_resp.text.strip():
                return _defer("Bear 空响应", round_num)
            bear_args.append(bear_resp.text.strip())

            # 冲突检测
            if _is_conflicting(bull_resp.text, bear_resp.text):
                return DecisionResult(
                    verdict="defer",
                    reason=f"Bull vs Bear 冲突（轮次 {round_num}）→ 升级人工",
                    rounds_used=round_num,
                    early_exit=True,
                    confidence=0.0,
                    requires_human_gate=True,
                    audit_id="",
                )

        # Judge 调解
        judge_req = GenerateRequest(
            role="judge",
            prompt=f"任务：{task_meta.content}\n卦象：{state.hexagram}\nBull：{'; '.join(bull_args)}\nBear：{'; '.join(bear_args)}\n请给出最终决策（approve/reject/defer）",
            context={"hexagram": state.hexagram},
            trace_id="judge-final",
        )
        try:
            judge_resp = self.llm_client.generate(judge_req)
        except Exception as e:
            return _defer(f"Judge 异常: {type(e).__name__}", max_rounds)

        if not judge_resp.ok or not judge_resp.text.strip():
            return _defer("Judge 空响应", max_rounds)

        verdict = _parse_verdict(judge_resp.text)
        confidence = bull_weight if verdict == "approve" else bear_weight

        audit_id = record_decision_audit(
            task_id=task_meta.task_id,
            system_state=sys_state,
            debate_policy=policy,
            debate_result={"bull": bull_args, "bear": bear_args, "judge": judge_resp.text},
            final_decision=verdict,
        )

        return DecisionResult(
            verdict=verdict,
            reason=judge_resp.text[:200],
            rounds_used=max_rounds,
            early_exit=False,
            confidence=confidence,
            requires_human_gate=(verdict == "defer"),
            audit_id=audit_id,
        )


def _defer(reason: str, rounds_used: int) -> DecisionResult:
    return DecisionResult(
        verdict="defer",
        reason=reason,
        rounds_used=rounds_used,
        early_exit=True,
        confidence=0.0,
        requires_human_gate=True,
        audit_id="",
    )


def _is_conflicting(bull_text: str, bear_text: str) -> bool:
    bull_lower = bull_text.lower()
    bear_lower = bear_text.lower()
    bull_approve = any(kw in bull_lower for kw in ["approve", "safe", "低风险", "可以"])
    bear_reject = any(kw in bear_lower for kw in ["reject", "high risk", "高风险", "不建议"])
    return bull_approve and bear_reject


def _parse_verdict(text: str) -> str:
    t = text.lower()
    if "approve" in t or "批准" in t:
        return "approve"
    elif "reject" in t or "拒绝" in t:
        return "reject"
    return "defer"

POLICY_VERSION = "v3.0"

# ============================================================
# 类型定义
# ============================================================

class SystemState(TypedDict):
    """系统状态快照"""
    evolution_score: float  # 0-100
    hexagram: str          # 卦名（如"坤卦"）
    hexagram_id: int       # 卦序号（1-64）
    timestamp: str         # ISO 8601
    confidence: float      # 置信度（0-1）


class DebatePolicy(TypedDict):
    """辩论策略配置"""
    bull_weight: float     # Bull 权重（0-1）
    bear_weight: float     # Bear 权重（0-1）
    max_rounds: int        # 最大轮次（1-5）
    flags: list[str]       # 特殊标记（如 "expert_review", "fast_track"）
    reason: str            # 策略原因
    policy_version: str    # Phase 2: 策略版本号（如 "v2.0"）
    requires_human_gate: bool  # Phase 2: 是否需要人工审批
    task_risk_level: str   # Phase 2: 任务风险等级（low/medium/high）


class DecisionAudit(TypedDict):
    """决策审计记录"""
    audit_id: str
    timestamp: str
    task_id: str
    system_state: SystemState
    debate_policy: DebatePolicy
    debate_result: Optional[dict]  # 辩论结果（Phase 2 填充）
    final_decision: Optional[str]  # 最终决策（Phase 2 填充）


# ============================================================
# 核心函数
# ============================================================

def get_system_state() -> SystemState:
    """
    拉取当前系统状态（Evolution Score + Hexagram）
    
    Returns:
        SystemState: 系统状态快照
    """
    workspace = Path(__file__).parent
    
    # 1. 读取 Evolution Score
    evolution_file = workspace / "evolution_score.json"
    try:
        with open(evolution_file, "r", encoding="utf-8") as f:
            evo_data = json.load(f)
            evolution_score = evo_data.get("evolution_score", 50.0)
            confidence = evo_data.get("confidence", 0.5)
    except Exception:
        evolution_score = 50.0  # 默认中性
        confidence = 0.5
    
    # 2. 读取当前卦象
    hexagram_file = workspace / "hexagram_state.json"
    try:
        with open(hexagram_file, "r", encoding="utf-8") as f:
            hex_data = json.load(f)
            hexagram = hex_data.get("hexagram", "坤卦")
            hexagram_id = hex_data.get("hexagram_id", 2)
    except Exception:
        hexagram = "坤卦"  # 默认坤卦（稳健）
        hexagram_id = 2
    
    return {
        "evolution_score": evolution_score,
        "hexagram": hexagram,
        "hexagram_id": hexagram_id,
        "timestamp": datetime.now().isoformat(),
        "confidence": confidence
    }


def build_debate_policy(state: SystemState) -> DebatePolicy:
    """
    根据系统状态生成辩论策略
    
    核心规则（Phase 1）：
    1. Evolution Score 映射权重：
       - 90-100: Bull 0.7 / Bear 0.3（激进）
       - 70-89:  Bull 0.6 / Bear 0.4（平衡偏激进）
       - 50-69:  Bull 0.5 / Bear 0.5（中性）
       - 30-49:  Bull 0.4 / Bear 0.6（保守）
       - 0-29:   Bull 0.3 / Bear 0.7（极保守）
    
    2. Hexagram 修正：
       - 大过卦（28）: 添加 "expert_review" flag
       - 既济卦（63）: 添加 "fast_track" flag（3轮快速通道）
       - 未济卦（64）: max_rounds = 5（深度辩论）
    
    3. 权重归一化：确保 bull_weight + bear_weight = 1.0
    
    Args:
        state: 系统状态快照
    
    Returns:
        DebatePolicy: 辩论策略配置
    """
    score = state["evolution_score"]
    hexagram_id = state["hexagram_id"]
    hexagram = state["hexagram"]
    
    # 1. 基础权重映射（Evolution Score）
    if score >= 90:
        bull_weight, bear_weight = 0.7, 0.3
        reason = f"Evolution Score {score:.1f} - 系统稳定，激进策略"
    elif score >= 70:
        bull_weight, bear_weight = 0.6, 0.4
        reason = f"Evolution Score {score:.1f} - 平衡偏激进"
    elif score >= 50:
        bull_weight, bear_weight = 0.5, 0.5
        reason = f"Evolution Score {score:.1f} - 中性策略"
    elif score >= 30:
        bull_weight, bear_weight = 0.4, 0.6
        reason = f"Evolution Score {score:.1f} - 保守策略"
    else:
        bull_weight, bear_weight = 0.3, 0.7
        reason = f"Evolution Score {score:.1f} - 极保守策略"
    
    # 2. 默认轮次
    max_rounds = 3
    flags = []
    
    # 3. Hexagram 修正
    if hexagram_id == 28:  # 大过卦
        flags.append("expert_review")
        reason += f" | {hexagram}：风险过高，需专家审查"
    
    elif hexagram_id == 63:  # 既济卦
        flags.append("fast_track")
        max_rounds = 3
        reason += f" | {hexagram}：系统稳定，快速通道"
    
    elif hexagram_id == 64:  # 未济卦
        max_rounds = 5
        reason += f" | {hexagram}：系统不稳，深度辩论"
    
    # 4. 权重归一化（防止浮点误差）
    total = bull_weight + bear_weight
    bull_weight = round(bull_weight / total, 2)
    bear_weight = round(bear_weight / total, 2)
    
    # Phase 1 返回（保持向后兼容）
    return {
        "bull_weight": bull_weight,
        "bear_weight": bear_weight,
        "max_rounds": max_rounds,
        "flags": flags,
        "reason": reason,
        "policy_version": "v1.0",
        "requires_human_gate": False,
        "task_risk_level": "medium"  # 默认中等风险
    }


def record_decision_audit(
    task_id: str,
    system_state: SystemState,
    debate_policy: DebatePolicy,
    debate_result: Optional[dict] = None,
    final_decision: Optional[str] = None
) -> str:
    """
    记录决策审计日志（JSONL 格式）
    
    Args:
        task_id: 任务 ID
        system_state: 系统状态快照
        debate_policy: 辩论策略配置
        debate_result: 辩论结果（Phase 2 填充）
        final_decision: 最终决策（Phase 2 填充）
    
    Returns:
        audit_id: 审计记录 ID
    """
    workspace = Path(__file__).parent
    audit_file = workspace / "decision_audit.jsonl"
    
    # 生成审计 ID
    audit_id = f"audit-{int(time.time() * 1000)}"
    
    # 构建审计记录
    audit: DecisionAudit = {
        "audit_id": audit_id,
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "system_state": system_state,
        "debate_policy": debate_policy,
        "debate_result": debate_result,
        "final_decision": final_decision
    }
    
    # 追加到 JSONL
    with open(audit_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit, ensure_ascii=False) + "\n")
    
    return audit_id


# ============================================================
# Phase 2: 动态策略覆盖（分数 × 卦象联合决策）
# ============================================================

class _TaskMetaV2(TypedDict):
    """任务元数据（Phase 2 内部用，已被 TaskMeta dataclass 取代）"""
    task_id: str
    task_type: str         # "code_change" | "config_update" | "data_migration" | "doc_update"
    risk_keywords: list[str]  # 高危关键词列表
    estimated_impact: str  # "low" | "medium" | "high"


def classify_task_risk(task_meta) -> str:
    """
    任务风险分级（Phase 2）
    
    规则：
    - high: 包含高危关键词 OR estimated_impact=high
    - medium: estimated_impact=medium OR 默认
    - low: task_type=doc_update AND 无高危关键词
    
    Args:
        task_meta: 任务元数据
    
    Returns:
        risk_level: "low" | "medium" | "high"
    """
    HIGH_RISK_KEYWORDS = {
        "删除", "迁移", "回滚", "生产环境", "数据库", "权限",
        "drop", "truncate", "delete", "migration", "production"
    }
    
    # 检查高危关键词
    has_high_risk = any(kw in task_meta.get("risk_keywords", []) for kw in HIGH_RISK_KEYWORDS)
    
    if has_high_risk or task_meta.get("estimated_impact") == "high":
        return "high"
    elif task_meta.get("task_type") == "doc_update" and not has_high_risk:
        return "low"
    elif task_meta.get("estimated_impact") == "low":
        return "low"
    else:
        return "medium"


def apply_phase2_overrides(
    policy: DebatePolicy,
    state: SystemState,
    task_meta
) -> DebatePolicy:
    """
    Phase 2 策略覆盖（分数 × 卦象 × 任务风险联合决策）
    
    核心规则：
    1. 任务风险分级 → task_risk_level
    2. 既济卦 fast_track 硬护栏：仅 low 风险可触发
    3. 大过卦 expert_review 升级为流程节点：
       - high 风险 → requires_human_gate=True（同步阻断）
       - medium/low 风险 → 异步补审（记录但不阻断）
    4. 高分+未济 / 低分+既济 特殊处理
    5. 策略版本号 v2.0
    
    Args:
        policy: Phase 1 生成的基础策略
        state: 系统状态
        task_meta: 任务元数据
    
    Returns:
        policy_v2: 覆盖后的策略
    """
    policy_v2 = policy.copy()
    policy_v2["policy_version"] = "v2.0"
    
    # 1. 任务风险分级
    risk_level = classify_task_risk(task_meta)
    policy_v2["task_risk_level"] = risk_level
    
    score = state["evolution_score"]
    hex_id = state["hexagram_id"]
    
    # 2. 既济卦 fast_track 硬护栏
    if "fast_track" in policy_v2["flags"]:
        if risk_level != "low":
            policy_v2["flags"].remove("fast_track")
            policy_v2["reason"] += f" | 既济卦快通道被禁用（任务风险={risk_level}）"
    
    # 3. 大过卦 expert_review 升级
    if "expert_review" in policy_v2["flags"]:
        if risk_level == "high":
            policy_v2["requires_human_gate"] = True
            policy_v2["reason"] += " | 大过卦+高风险 → 同步人工审批"
        else:
            policy_v2["reason"] += " | 大过卦+中低风险 → 异步补审"
    
    # 4. 特殊场景处理
    # 场景 A: 高分+未济（系统稳定但卦象不稳）→ 降低轮次
    if score >= 85 and hex_id == 64:
        policy_v2["max_rounds"] = 3
        policy_v2["reason"] += " | 高分+未济 → 降低轮次至3（信任系统稳定性）"
    
    # 场景 B: 低分+既济（系统不稳但卦象完成）→ 取消快通道
    if score < 60 and hex_id == 63:
        if "fast_track" in policy_v2["flags"]:
            policy_v2["flags"].remove("fast_track")
        policy_v2["max_rounds"] = 4
        policy_v2["reason"] += " | 低分+既济 → 取消快通道，增加轮次至4"
    
    # 场景 C: 高风险+既济（快通道与高风险冲突）→ 已在步骤2处理
    
    # 场景 D: 大过+高分（危机但系统稳定）→ 降级为异步补审
    if hex_id == 28 and score >= 85:
        policy_v2["requires_human_gate"] = False
        policy_v2["reason"] += " | 大过+高分 → 降级为异步补审（信任系统稳定性）"
    
    return policy_v2


# ============================================================
# Phase 1.5: 异常降级与默认兜底
# ============================================================

def get_system_state_safe() -> SystemState:
    """
    安全版本的 get_system_state()
    
    异常降级规则：
    - Evolution Score 无效 → 50.0（中性）
    - Hexagram 无效 → 坤卦（稳健）
    - 文件不存在 → 使用默认值
    """
    try:
        return get_system_state()
    except Exception as e:
        print(f"[WARN] get_system_state() failed: {e}, using defaults")
        return {
            "evolution_score": 50.0,
            "hexagram": "坤卦",
            "hexagram_id": 2,
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.5
        }


def build_debate_policy_safe(state: SystemState) -> DebatePolicy:
    """
    安全版本的 build_debate_policy()
    
    异常降级规则：
    - 任何异常 → 返回中性策略（0.5/0.5, 3 rounds）
    """
    try:
        return build_debate_policy(state)
    except Exception as e:
        print(f"[WARN] build_debate_policy() failed: {e}, using neutral policy")
        return {
            "bull_weight": 0.5,
            "bear_weight": 0.5,
            "max_rounds": 3,
            "flags": [],
            "reason": "异常降级：使用中性策略"
        }


# ============================================================
# Phase 3: 核心执行器与降级路径
# ============================================================

def generate_prompt_hash(prompt: str) -> str:
    """生成 prompt 的 SHA256 哈希（前16位）"""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def send_telegram_alert(message: str) -> bool:
    """
    发送 Telegram 告警（同步直发版本）
    
    失败只记录，不抛异常阻塞主链路
    
    Args:
        message: 告警消息
    
    Returns:
        bool: 是否发送成功
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = "7986452220"  # 珊瑚海
    
    if not token:
        # 避免 emoji 编码问题
        safe_msg = message.encode('utf-8', errors='ignore').decode('utf-8')[:50]
        print(f"[WARN] TELEGRAM_BOT_TOKEN not set, alert not sent: {safe_msg}...")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            success = 200 <= r.status < 300
            if success:
                safe_msg = message.encode('utf-8', errors='ignore').decode('utf-8')[:50]
                print(f"[OK] Telegram alert sent: {safe_msg}...")
            return success
    except Exception as e:
        safe_msg = message.encode('utf-8', errors='ignore').decode('utf-8')[:50]
        print(f"[WARN] Telegram alert failed: {e}, message: {safe_msg}...")
        return False


def execute_debate_round(
    state: dict,
    prompt: str,
    llm_generate_func,
    role: str = "debater"
) -> dict:
    """
    执行单轮辩论，包含硬门槛校验和降级策略
    
    统一出口：所有 verdict 都走这里
    
    Args:
        state: 系统状态（包含 flags/hexagram_id 等）
        prompt: 辩论 prompt
        llm_generate_func: LLM 生成函数（模拟或真实）
        role: 角色名称（bull/bear/expert）
    
    Returns:
        decision: {
            "verdict": "approve" | "reject" | "defer",
            "confidence": float,
            "reason": str,
            "requires_human_gate": bool,
            "fast_track": bool,
            "_audit_meta": {
                "prompt_hash": str,
                "latency_ms": int,
                "alert_sent": bool,
                "policy_version": str
            }
        }
    """
    started_ms = int(time.time() * 1000)
    prompt_hash = generate_prompt_hash(prompt)
    alert_sent = False
    
    # 降级路径 1: 模型彻底失败或返回空响应
    try:
        response_text = llm_generate_func(prompt)
    except Exception as e:
        print(f"[SRE] 模型调用失败: {e}，触发保守降级策略！")
        alert_msg = f"🚨 [AIOS 告警] 辩论模型不可用\n\n角色: {role}\n错误: {e}\n已触发保守降级！"
        alert_sent = send_telegram_alert(alert_msg)
        
        return {
            "verdict": "reject",
            "confidence": 0.0,
            "reason": f"System Fallback: LLM Exception ({type(e).__name__})",
            "requires_human_gate": True,
            "fast_track": False,
            "_audit_meta": {
                "prompt_hash": prompt_hash,
                "latency_ms": int(time.time() * 1000) - started_ms,
                "alert_sent": alert_sent,
                "policy_version": POLICY_VERSION
            }
        }
    
    if not response_text:
        print("[SRE] 模型返回空响应，触发保守降级策略！")
        alert_msg = f"🚨 [AIOS 告警] 辩论模型返回空响应\n\n角色: {role}\n已触发保守降级！"
        alert_sent = send_telegram_alert(alert_msg)
        
        return {
            "verdict": "reject",
            "confidence": 0.0,
            "reason": "System Fallback: LLM Timeout or Empty Response",
            "requires_human_gate": True,
            "fast_track": False,
            "_audit_meta": {
                "prompt_hash": prompt_hash,
                "latency_ms": int(time.time() * 1000) - started_ms,
                "alert_sent": alert_sent,
                "policy_version": POLICY_VERSION
            }
        }
    
    # 降级路径 2: 输出格式冲突/崩溃
    try:
        decision = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[SRE] 模型输出格式崩溃: {e}，触发保守降级策略！")
        alert_msg = f"🚨 [AIOS 告警] 辩论模型输出格式崩溃\n\n角色: {role}\n错误: {e}\n响应: {response_text[:100]}...\n已触发保守降级！"
        alert_sent = send_telegram_alert(alert_msg)
        
        return {
            "verdict": "reject",
            "confidence": 0.0,
            "reason": "System Fallback: LLM Output Format Corrupted",
            "requires_human_gate": True,
            "fast_track": False,
            "_audit_meta": {
                "prompt_hash": prompt_hash,
                "latency_ms": int(time.time() * 1000) - started_ms,
                "alert_sent": alert_sent,
                "policy_version": POLICY_VERSION
            }
        }
    
    # 硬门槛：大过卦（高风险）不可被 fast_track 或高置信度覆盖
    if state.get("flags", {}).get("expert_review") is True:
        decision["requires_human_gate"] = True
        decision["verdict"] = "reject"  # 强制挂起等待审查
        decision["fast_track"] = False
        decision["reason"] = f"[大过卦硬拦截] {decision.get('reason', '')}"
        print(f"[GATE] 大过卦硬拦截触发: {decision['reason']}")
    
    # 添加审计元数据
    decision["_audit_meta"] = {
        "prompt_hash": prompt_hash,
        "latency_ms": int(time.time() * 1000) - started_ms,
        "alert_sent": alert_sent,
        "policy_version": POLICY_VERSION
    }
    
    return decision


# ============================================================
# 测试入口（Phase 1 验证）
# ============================================================

def test_phase1():
    """Phase 1 完整流程测试"""
    print("=" * 60)
    print("Debate Policy Engine - Phase 1 Test")
    print("=" * 60)
    
    # 1. 获取系统状态
    print("\n[1] 获取系统状态...")
    state = get_system_state_safe()
    print(f"  Evolution Score: {state['evolution_score']:.1f}")
    print(f"  Hexagram: {state['hexagram']} (#{state['hexagram_id']})")
    print(f"  Confidence: {state['confidence']:.2f}")
    
    # 2. 生成辩论策略
    print("\n[2] 生成辩论策略...")
    policy = build_debate_policy_safe(state)
    print(f"  Bull Weight: {policy['bull_weight']:.2f}")
    print(f"  Bear Weight: {policy['bear_weight']:.2f}")
    print(f"  Max Rounds: {policy['max_rounds']}")
    print(f"  Flags: {policy['flags']}")
    print(f"  Reason: {policy['reason']}")
    
    # 3. 记录审计日志
    print("\n[3] 记录审计日志...")
    audit_id = record_decision_audit(
        task_id="test-task-001",
        system_state=state,
        debate_policy=policy
    )
    print(f"  Audit ID: {audit_id}")
    print(f"  Audit File: decision_audit.jsonl")
    
    print("\n" + "=" * 60)
    print("[OK] Phase 1 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_phase1()
