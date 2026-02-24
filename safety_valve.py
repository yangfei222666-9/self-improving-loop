"""
Self-Improving Agent 安全阀和风险控制
防止误修、振荡、系统带偏
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

AIOS_ROOT = Path(__file__).resolve().parent.parent
SAFETY_DIR = AIOS_ROOT / "agent_system" / "data" / "safety"
SAFETY_DIR.mkdir(parents=True, exist_ok=True)

COOLDOWN_STATE = SAFETY_DIR / "cooldown_state.json"
CIRCUIT_BREAKER_STATE = SAFETY_DIR / "circuit_breaker_state.json"


class SafetyValve:
    """安全阀：防止过度改进和振荡"""

    # 风险白名单：只有这些改进类型允许自动应用
    LOW_RISK_WHITELIST = {
        "increase_timeout",      # 增加超时时间
        "add_retry",             # 添加重试机制
        "rate_limiting",         # 限流
        "agent_degradation",     # 降低 Agent 优先级
        "thinking_level_adjust", # 调整 thinking level
    }

    # 高风险黑名单：这些操作一律需要人工确认
    HIGH_RISK_BLACKLIST = {
        "delete_file",
        "restart_service",
        "kill_process",
        "modify_permissions",
        "install_dependency",
    }

    def __init__(self):
        self.cooldown_state = self._load_cooldown_state()
        self.circuit_breaker_state = self._load_circuit_breaker_state()

    def is_allowed(
        self,
        improvement_type: str,
        target: str,
        allow_risk_level: str = "low"
    ) -> tuple[bool, str]:
        """
        检查改进是否允许应用
        
        Args:
            improvement_type: 改进类型
            target: 改进目标（agent_id/config_key/tool_name）
            allow_risk_level: 允许的风险等级（low/medium/high）
        
        Returns:
            (是否允许, 原因)
        """
        # 1. 检查熔断器
        if self._is_circuit_broken():
            return False, "熔断器已触发，24h 内禁止自动改进"

        # 2. 检查风险等级
        if improvement_type in self.HIGH_RISK_BLACKLIST:
            return False, f"高风险操作 {improvement_type}，需要人工确认"

        if allow_risk_level == "low" and improvement_type not in self.LOW_RISK_WHITELIST:
            return False, f"非低风险操作 {improvement_type}，当前只允许 low 风险"

        # 3. 检查冷却期
        if self._is_in_cooldown(improvement_type, target):
            last_time = self.cooldown_state.get(f"{improvement_type}:{target}", {}).get("last_applied")
            return False, f"冷却期内（上次应用: {last_time}），24h 内不重复应用"

        return True, "通过安全检查"

    def record_application(self, improvement_type: str, target: str, success: bool):
        """记录改进应用"""
        key = f"{improvement_type}:{target}"
        now = datetime.now().isoformat()

        # 更新冷却状态
        self.cooldown_state[key] = {
            "last_applied": now,
            "success": success,
        }
        self._save_cooldown_state()

        # 更新熔断器状态
        if not success:
            self._record_failure()
        else:
            self._record_success()

    def _is_in_cooldown(self, improvement_type: str, target: str) -> bool:
        """检查是否在冷却期内（24小时）"""
        key = f"{improvement_type}:{target}"
        if key not in self.cooldown_state:
            return False

        last_applied = self.cooldown_state[key].get("last_applied")
        if not last_applied:
            return False

        last_time = datetime.fromisoformat(last_applied)
        now = datetime.now()

        return (now - last_time) < timedelta(hours=24)

    def _is_circuit_broken(self) -> bool:
        """检查熔断器是否触发"""
        if not self.circuit_breaker_state.get("broken"):
            return False

        broken_at = self.circuit_breaker_state.get("broken_at")
        if not broken_at:
            return False

        broken_time = datetime.fromisoformat(broken_at)
        now = datetime.now()

        # 24 小时后自动恢复
        if (now - broken_time) > timedelta(hours=24):
            self._reset_circuit_breaker()
            return False

        return True

    def _record_failure(self):
        """记录失败，连续失败 ≥2 次触发熔断"""
        failures = self.circuit_breaker_state.get("consecutive_failures", 0) + 1
        self.circuit_breaker_state["consecutive_failures"] = failures

        if failures >= 2:
            self.circuit_breaker_state["broken"] = True
            self.circuit_breaker_state["broken_at"] = datetime.now().isoformat()
            print("⚠️ 熔断器触发：连续失败 ≥2 次，24h 内禁止自动改进")

        self._save_circuit_breaker_state()

    def _record_success(self):
        """记录成功，重置连续失败计数"""
        self.circuit_breaker_state["consecutive_failures"] = 0
        self._save_circuit_breaker_state()

    def _reset_circuit_breaker(self):
        """重置熔断器"""
        self.circuit_breaker_state = {
            "broken": False,
            "broken_at": None,
            "consecutive_failures": 0,
        }
        self._save_circuit_breaker_state()
        print("✓ 熔断器已恢复")

    def _load_cooldown_state(self) -> Dict:
        """加载冷却状态"""
        if COOLDOWN_STATE.exists():
            with open(COOLDOWN_STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cooldown_state(self):
        """保存冷却状态"""
        with open(COOLDOWN_STATE, "w", encoding="utf-8") as f:
            json.dump(self.cooldown_state, f, ensure_ascii=False, indent=2)

    def _load_circuit_breaker_state(self) -> Dict:
        """加载熔断器状态"""
        if CIRCUIT_BREAKER_STATE.exists():
            with open(CIRCUIT_BREAKER_STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "broken": False,
            "broken_at": None,
            "consecutive_failures": 0,
        }

    def _save_circuit_breaker_state(self):
        """保存熔断器状态"""
        with open(CIRCUIT_BREAKER_STATE, "w", encoding="utf-8") as f:
            json.dump(self.circuit_breaker_state, f, ensure_ascii=False, indent=2)


def test_safety_valve():
    """测试安全阀"""
    valve = SafetyValve()

    # 测试 1: 低风险操作
    allowed, reason = valve.is_allowed("increase_timeout", "agent_001", "low")
    print(f"低风险操作: {allowed} - {reason}")

    # 测试 2: 高风险操作
    allowed, reason = valve.is_allowed("delete_file", "test.txt", "low")
    print(f"高风险操作: {allowed} - {reason}")

    # 测试 3: 冷却期
    valve.record_application("increase_timeout", "agent_001", True)
    allowed, reason = valve.is_allowed("increase_timeout", "agent_001", "low")
    print(f"冷却期检查: {allowed} - {reason}")

    # 测试 4: 熔断器
    valve.record_application("test_fix", "agent_002", False)
    valve.record_application("test_fix", "agent_002", False)
    allowed, reason = valve.is_allowed("increase_timeout", "agent_003", "low")
    print(f"熔断器检查: {allowed} - {reason}")


if __name__ == "__main__":
    test_safety_valve()
