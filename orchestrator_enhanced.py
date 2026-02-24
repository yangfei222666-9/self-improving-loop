# aios/agent_system/orchestrator_enhanced.py - 增强版 Orchestrator
"""
AIOS Agent Orchestrator Enhanced
增强的协调器，包含：
1. 智能决策逻辑
2. 资源调度优化
3. 优先级管理
4. 动态调整
"""

import json
from pathlib import Path
from datetime import datetime
import time


class EnhancedOrchestrator:
    """增强版 Orchestrator"""

    def __init__(self):
        self.workspace = Path(r"C:\Users\A\.openclaw\workspace\aios")
        self.log_file = self.workspace / "orchestrator_enhanced.log"
        self.state_file = Path(
            r"C:\Users\A\.openclaw\workspace\memory\selflearn-state.json"
        )

        # Agent 配置（增强版）
        self.agents = {
            "monitor": {
                "last_run": None,
                "interval_minutes": 5,
                "priority": "high",
                "max_duration": 30,  # 最大执行时间（秒）
                "retry_on_failure": True,
                "dependencies": [],
            },
            "analyst": {
                "last_run": None,
                "interval_minutes": 1440,
                "priority": "medium",
                "max_duration": 300,
                "retry_on_failure": False,
                "dependencies": ["monitor"],
            },
            "optimizer": {
                "last_run": None,
                "interval_minutes": 60,
                "priority": "high",
                "max_duration": 120,
                "retry_on_failure": True,
                "dependencies": ["analyst"],
            },
            "executor": {
                "last_run": None,
                "interval_minutes": 30,
                "priority": "critical",
                "max_duration": 180,
                "retry_on_failure": True,
                "dependencies": ["optimizer"],
            },
            "validator": {
                "last_run": None,
                "interval_minutes": 1440,
                "priority": "medium",
                "max_duration": 300,
                "retry_on_failure": False,
                "dependencies": ["executor"],
            },
            "learner": {
                "last_run": None,
                "interval_minutes": 1440,
                "priority": "low",
                "max_duration": 300,
                "retry_on_failure": False,
                "dependencies": ["validator"],
            },
        }

        # 资源限制
        self.max_concurrent_agents = 2
        self.running_agents = set()

        # 决策历史
        self.decision_history = []

    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

        try:
            print(log_entry.strip())
        except UnicodeEncodeError:
            print(log_entry.encode("ascii", "ignore").decode("ascii").strip())

    def should_run_agent(self, agent_name):
        """智能决策：是否应该运行 Agent"""
        agent = self.agents[agent_name]

        # 1. 检查时间间隔
        last_run = agent["last_run"]
        interval = agent["interval_minutes"]

        if last_run is not None:
            elapsed = (datetime.now() - last_run).total_seconds() / 60
            if elapsed < interval:
                return False, "时间未到"

        # 2. 检查依赖
        for dep in agent["dependencies"]:
            dep_agent = self.agents[dep]
            if dep_agent["last_run"] is None:
                return False, f"依赖 {dep} 未运行"

        # 3. 检查资源
        if len(self.running_agents) >= self.max_concurrent_agents:
            return False, "资源不足"

        # 4. 检查优先级（如果有更高优先级的 Agent 等待）
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        current_priority = priority_order[agent["priority"]]

        for other_name, other_agent in self.agents.items():
            if other_name == agent_name:
                continue
            if other_agent["last_run"] is None:
                continue

            other_priority = priority_order[other_agent["priority"]]
            if other_priority < current_priority:
                # 有更高优先级的 Agent
                other_elapsed = (
                    datetime.now() - other_agent["last_run"]
                ).total_seconds() / 60
                if other_elapsed >= other_agent["interval_minutes"]:
                    return False, f"优先级低于 {other_name}"

        return True, "可以运行"

    def run_agent(self, agent_name):
        """运行 Agent（带超时和重试）"""
        agent = self.agents[agent_name]
        max_duration = agent["max_duration"]
        retry_on_failure = agent["retry_on_failure"]

        self.log(f"开始运行 {agent_name}", "INFO")
        self.running_agents.add(agent_name)

        try:
            # 运行 Agent 脚本
            import subprocess

            script_path = self.workspace / "agent_system" / f"{agent_name}_agent.py"

            if not script_path.exists():
                self.log(f"{agent_name} 脚本不存在", "WARN")
                return False

            result = subprocess.run(
                [
                    r"C:\Program Files\Python312\python.exe",
                    "-X",
                    "utf8",
                    str(script_path),
                ],
                capture_output=True,
                text=True,
                timeout=max_duration,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                self.log(f"{agent_name} 执行成功", "INFO")
                agent["last_run"] = datetime.now()
                return True
            else:
                self.log(f"{agent_name} 执行失败: {result.stderr[:200]}", "ERROR")

                if retry_on_failure:
                    self.log(f"重试 {agent_name}", "INFO")
                    time.sleep(5)
                    return self.run_agent(agent_name)

                return False

        except subprocess.TimeoutExpired:
            self.log(f"{agent_name} 超时（>{max_duration}s）", "ERROR")
            return False
        except Exception as e:
            self.log(f"{agent_name} 异常: {e}", "ERROR")
            return False
        finally:
            self.running_agents.discard(agent_name)

    def optimize_schedule(self):
        """优化调度策略"""
        # 根据历史数据动态调整间隔
        for agent_name, agent in self.agents.items():
            # 如果 Agent 经常失败，增加间隔
            # 如果 Agent 很成功，可以减少间隔
            pass

    def run_cycle(self):
        """运行一个完整周期"""
        self.log("=" * 50)
        self.log("开始 Orchestrator 增强周期")
        self.log("=" * 50)

        # 按优先级排序
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_agents = sorted(
            self.agents.items(), key=lambda x: priority_order[x[1]["priority"]]
        )

        executed = []
        skipped = []

        for agent_name, agent in sorted_agents:
            should_run, reason = self.should_run_agent(agent_name)

            if should_run:
                success = self.run_agent(agent_name)
                if success:
                    executed.append(agent_name)
                else:
                    skipped.append((agent_name, "执行失败"))
            else:
                skipped.append((agent_name, reason))

        # 记录决策
        decision = {
            "timestamp": datetime.now().isoformat(),
            "executed": executed,
            "skipped": skipped,
        }
        self.decision_history.append(decision)

        self.log(f"执行了 {len(executed)} 个 Agent: {executed}")
        self.log(f"跳过了 {len(skipped)} 个 Agent")

        # 更新时间戳
        self.update_timestamp()

        self.log("=" * 50)
        self.log("周期完成")
        self.log("=" * 50)

    def update_timestamp(self):
        """更新时间戳"""
        state = {}
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

        state["last_orchestrator"] = datetime.now().isoformat()

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)


def main():
    orchestrator = EnhancedOrchestrator()
    orchestrator.run_cycle()


if __name__ == "__main__":
    main()
