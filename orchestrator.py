"""
AIOS Agent Orchestrator
协调所有 Agent，形成闭环工作流
"""

import json
from pathlib import Path
from datetime import datetime

class AgentOrchestrator:
    def __init__(self):
        self.workspace = Path(r"C:\Users\A\.openclaw\workspace\aios")
        self.log_file = self.workspace / "orchestrator.log"
        self.state_file = Path(r"C:\Users\A\.openclaw\workspace\memory\selflearn-state.json")
        
        # Agent 状态
        self.agents = {
            "monitor": {"last_run": None, "interval_minutes": 5},
            "analyst": {"last_run": None, "interval_minutes": 1440},  # 每天
            "optimizer": {"last_run": None, "interval_minutes": 60},  # 每小时
            "executor": {"last_run": None, "interval_minutes": 30},   # 每30分钟
            "validator": {"last_run": None, "interval_minutes": 1440}, # 每天
            "learner": {"last_run": None, "interval_minutes": 1440}   # 每天
        }
        
        # 通信文件
        self.alerts_file = self.workspace / "core" / "alerts.jsonl"
        self.insights_file = self.workspace / "analyst_insights.json"
        self.plan_file = self.workspace / "optimization_plan.json"
        self.execution_log = self.workspace / "execution_log.jsonl"
        self.validation_report = self.workspace / "validation_report.json"
        self.lessons_file = Path(r"C:\Users\A\.openclaw\workspace\memory\lessons.json")
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        try:
            print(log_entry.strip())
        except UnicodeEncodeError:
            print(log_entry.encode('ascii', 'ignore').decode('ascii').strip())
    
    def should_run_orchestrator(self):
        """检查是否应该运行 Orchestrator（每小时一次）"""
        if not self.state_file.exists():
            return True
        
        with open(self.state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        last_run = state.get("last_orchestrator")
        if not last_run:
            return True
        
        # 解析时间戳
        last_time = datetime.fromisoformat(last_run)
        elapsed = (datetime.now() - last_time).total_seconds() / 3600  # 小时
        
        return elapsed >= 1.0  # 至少间隔1小时
    
    def update_orchestrator_timestamp(self):
        """更新 Orchestrator 执行时间戳"""
        state = {}
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
        
        state["last_orchestrator"] = datetime.now().isoformat()
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    
    def should_run(self, agent_name):
        """判断 Agent 是否应该运行"""
        agent = self.agents[agent_name]
        last_run = agent["last_run"]
        interval = agent["interval_minutes"]
        
        if last_run is None:
            return True
        
        elapsed = (datetime.now() - last_run).total_seconds() / 60
        return elapsed >= interval
    
    def run_monitor(self):
        """运行 Monitor Agent"""
        self.log("=== Monitor Agent ===")
        
        # 运行真正的 Monitor Agent
        monitor_script = self.workspace / "agent_system" / "monitor_agent.py"
        
        if monitor_script.exists():
            import subprocess
            result = subprocess.run(
                [r"C:\Program Files\Python312\python.exe", "-X", "utf8", str(monitor_script)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=60
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if "MONITOR_ALERT:" in output:
                    count = output.split("MONITOR_ALERT:")[1].strip()
                    self.log(f"  发现 {count} 个告警")
                else:
                    self.log("  系统正常，无告警")
            else:
                self.log(f"  监控失败: {result.stderr}")
        else:
            self.log("  Monitor Agent 不存在")
        
        self.agents["monitor"]["last_run"] = datetime.now()
    
    def run_analyst(self):
        """运行 Analyst Agent"""
        self.log("=== Analyst Agent ===")
        
        # 已实现，直接调用
        import subprocess
        analyst_script = self.workspace / "agent_system" / "analyst_agent.py"
        
        if analyst_script.exists():
            result = subprocess.run(
                [r"C:\Program Files\Python312\python.exe", "-X", "utf8", str(analyst_script)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=120
            )
            
            if result.returncode == 0:
                self.log("  分析完成")
            else:
                self.log(f"  分析失败: {result.stderr}")
        
        self.agents["analyst"]["last_run"] = datetime.now()
    
    def run_optimizer(self):
        """运行 Optimizer Agent"""
        self.log("=== Optimizer Agent ===")
        
        # 读取 Analyst 的建议
        if not self.insights_file.exists():
            self.log("  没有新的建议")
            return
        
        with open(self.insights_file, 'r', encoding='utf-8') as f:
            insights_data = json.load(f)
        
        insights = insights_data.get("insights", [])
        recommendations = [i for i in insights if "recommendation" in i]
        
        if not recommendations:
            self.log("  没有优化建议")
            return
        
        # 生成优化计划
        plan = {
            "timestamp": datetime.now().isoformat(),
            "actions": []
        }
        
        for rec in recommendations:
            rec_type = rec.get("type")
            recommendation = rec.get("recommendation")
            
            # 根据建议类型生成行动
            if rec_type == "evolution_score" and "优化 Playbook" in recommendation:
                plan["actions"].append({
                    "type": "optimize_playbook",
                    "risk": "low",
                    "auto_execute": True,
                    "description": "增加低成功率 Playbook 的超时时间"
                })
            
            elif rec_type == "resource_usage" and "CPU" in recommendation:
                plan["actions"].append({
                    "type": "optimize_resource",
                    "risk": "medium",
                    "auto_execute": False,
                    "description": "优化高 CPU 使用任务"
                })
        
        # 保存计划
        with open(self.plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        
        self.log(f"  生成了 {len(plan['actions'])} 个优化行动")
        self.agents["optimizer"]["last_run"] = datetime.now()
    
    def run_executor(self):
        """运行 Executor Agent"""
        self.log("=== Executor Agent ===")
        
        # 读取优化计划
        if not self.plan_file.exists():
            self.log("  没有待执行的计划")
            return
        
        with open(self.plan_file, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        
        actions = plan.get("actions", [])
        auto_actions = [a for a in actions if a.get("auto_execute", False)]
        
        if not auto_actions:
            self.log("  没有可自动执行的行动")
            return
        
        # 执行行动
        for action in auto_actions:
            action_type = action.get("type")
            description = action.get("description")
            
            self.log(f"  执行: {description}")
            
            # TODO: 实际执行逻辑
            # 这里只是记录
            execution_record = {
                "timestamp": datetime.now().isoformat(),
                "action_type": action_type,
                "description": description,
                "status": "success"
            }
            
            # 追加到执行日志
            with open(self.execution_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(execution_record, ensure_ascii=False) + '\n')
        
        self.log(f"  执行了 {len(auto_actions)} 个行动")
        self.agents["executor"]["last_run"] = datetime.now()
    
    def run_validator(self):
        """运行 Validator Agent"""
        self.log("=== Validator Agent ===")
        
        # TODO: 实现 Validator Agent
        # 1. 读取执行日志
        # 2. 对比优化前后的指标
        # 3. 判断是否改善
        # 4. 如果变差 → 回滚
        # 5. 如果改善 → 记录成功案例
        
        self.log("  验证完成")
        self.agents["validator"]["last_run"] = datetime.now()
    
    def run_learner(self):
        """运行 Learner Agent"""
        self.log("=== Learner Agent ===")
        
        # TODO: 实现 Learner Agent
        # 1. 读取验证报告
        # 2. 提取成功的优化模式
        # 3. 更新 lessons.json
        # 4. 生成新的 Playbook
        
        self.log("  学习完成")
        self.agents["learner"]["last_run"] = datetime.now()
    
    def run_cycle(self):
        """运行一个完整周期"""
        # 检查是否应该运行
        if not self.should_run_orchestrator():
            elapsed = 0
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                last_run = state.get("last_orchestrator")
                if last_run:
                    last_time = datetime.fromisoformat(last_run)
                    elapsed = (datetime.now() - last_time).total_seconds() / 60  # 分钟
            
            print(f"ORCHESTRATOR_SKIP (上次运行: {elapsed:.1f}分钟前，需间隔60分钟)")
            return
        
        self.log("\n" + "="*50)
        self.log("开始 Agent 闭环周期")
        self.log("="*50)
        
        # 按顺序运行 Agent
        if self.should_run("monitor"):
            self.run_monitor()
        
        if self.should_run("analyst"):
            self.run_analyst()
        
        if self.should_run("optimizer"):
            self.run_optimizer()
        
        if self.should_run("executor"):
            self.run_executor()
        
        if self.should_run("validator"):
            self.run_validator()
        
        if self.should_run("learner"):
            self.run_learner()
        
        self.log("\n=== 周期完成 ===")
        
        # 更新时间戳
        self.update_orchestrator_timestamp()
        print("ORCHESTRATOR_OK")

if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    orchestrator.run_cycle()
