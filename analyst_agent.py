"""
AIOS Analyst Agent
分析历史数据，找出问题根因，生成优化建议
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

class AIOSAnalystAgent:
    def __init__(self):
        self.workspace = Path(r"C:\Users\A\.openclaw\workspace\aios")
        self.memory_dir = Path(r"C:\Users\A\.openclaw\workspace\memory")
        self.log_file = self.workspace / "analyst.log"
    
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
    
    def analyze_evolution_score(self):
        """分析 Evolution Score 趋势"""
        self.log("=== 分析 Evolution Score 趋势 ===")
        
        metrics_file = self.workspace / "learning" / "metrics_history.jsonl"
        if not metrics_file.exists():
            self.log("⏭️ 没有历史数据")
            return None
        
        # 读取最近7天的数据
        cutoff_date = datetime.now() - timedelta(days=7)
        scores = []
        
        with open(metrics_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    metric = json.loads(line)
                    ts = metric.get("ts", "")
                    score = metric.get("evolution_score", 0)
                    
                    if ts:
                        metric_time = datetime.fromisoformat(ts)
                        if metric_time > cutoff_date:
                            scores.append({
                                "time": ts,
                                "score": score,
                                "grade": metric.get("grade", "unknown")
                            })
                except:
                    pass
        
        if not scores:
            self.log("⏭️ 没有最近7天的数据")
            return None
        
        # 计算趋势
        avg_score = sum(s["score"] for s in scores) / len(scores)
        min_score = min(s["score"] for s in scores)
        max_score = max(s["score"] for s in scores)
        
        # 判断趋势
        if len(scores) >= 2:
            recent_avg = sum(s["score"] for s in scores[-3:]) / min(3, len(scores))
            old_avg = sum(s["score"] for s in scores[:3]) / min(3, len(scores))
            
            if recent_avg > old_avg + 0.1:
                trend = "improving"
            elif recent_avg < old_avg - 0.1:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "unknown"
        
        insight = {
            "type": "evolution_score",
            "avg_score": round(avg_score, 2),
            "min_score": round(min_score, 2),
            "max_score": round(max_score, 2),
            "trend": trend,
            "data_points": len(scores)
        }
        
        self.log(f"  平均分: {avg_score:.2f}")
        self.log(f"  最低分: {min_score:.2f}")
        self.log(f"  最高分: {max_score:.2f}")
        self.log(f"  趋势: {trend}")
        
        # 生成建议
        if trend == "degrading":
            insight["recommendation"] = "Evolution Score 下降，建议检查最近的 Playbook 执行情况"
        elif avg_score < 0.5:
            insight["recommendation"] = "平均分偏低，建议优化 Playbook 或增加资源"
        
        return insight
    
    def analyze_playbook_performance(self):
        """分析 Playbook 成功率"""
        self.log("=== 分析 Playbook 性能 ===")
        
        events_file = self.workspace / "data" / "events.jsonl"
        if not events_file.exists():
            self.log("⏭️ 没有事件数据")
            return None
        
        # 统计 Playbook 执行情况
        playbook_stats = defaultdict(lambda: {"success": 0, "failed": 0, "total": 0})
        
        with open(events_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line)
                    event_type = event.get("type", "")
                    
                    if event_type == "playbook.executed":
                        playbook_id = event.get("data", {}).get("playbook_id", "unknown")
                        success = event.get("data", {}).get("success", False)
                        
                        playbook_stats[playbook_id]["total"] += 1
                        if success:
                            playbook_stats[playbook_id]["success"] += 1
                        else:
                            playbook_stats[playbook_id]["failed"] += 1
                except:
                    pass
        
        if not playbook_stats:
            self.log("⏭️ 没有 Playbook 执行记录")
            return None
        
        # 计算成功率
        playbook_performance = []
        for playbook_id, stats in playbook_stats.items():
            success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            playbook_performance.append({
                "playbook_id": playbook_id,
                "success_rate": round(success_rate, 2),
                "total": stats["total"],
                "success": stats["success"],
                "failed": stats["failed"]
            })
        
        # 排序（成功率从低到高）
        playbook_performance.sort(key=lambda x: x["success_rate"])
        
        self.log(f"  分析了 {len(playbook_performance)} 个 Playbook")
        
        # 找出问题 Playbook
        low_performance = [p for p in playbook_performance if p["success_rate"] < 0.7 and p["total"] >= 3]
        
        if low_performance:
            self.log(f"  发现 {len(low_performance)} 个低成功率 Playbook:")
            for p in low_performance:
                self.log(f"    - {p['playbook_id']}: {p['success_rate']*100:.0f}% ({p['success']}/{p['total']})")
        
        insight = {
            "type": "playbook_performance",
            "total_playbooks": len(playbook_performance),
            "low_performance_count": len(low_performance),
            "low_performance": low_performance
        }
        
        # 生成建议
        if low_performance:
            insight["recommendation"] = f"有 {len(low_performance)} 个 Playbook 成功率低于 70%，建议优化或禁用"
        
        return insight
    
    def analyze_agent_failures(self):
        """分析 Agent 失败模式"""
        self.log("=== 分析 Agent 失败模式 ===")
        
        agents_file = self.workspace / "agent_system" / "agents.jsonl"
        if not agents_file.exists():
            self.log("⏭️ 没有 Agent 数据")
            return None
        
        # 读取 Agent 状态
        agents = []
        with open(agents_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    agent = json.loads(line)
                    agents.append(agent)
                except:
                    pass
        
        if not agents:
            self.log("⏭️ 没有 Agent 记录")
            return None
        
        # 统计失败情况
        total_agents = len(agents)
        degraded_agents = [a for a in agents if a.get("state") == "degraded"]
        blocked_agents = [a for a in agents if a.get("state") == "blocked"]
        
        # 统计错误类型
        error_types = defaultdict(int)
        for agent in agents:
            error_count = agent.get("error_count", 0)
            if error_count > 0:
                last_error = agent.get("last_error", "unknown")
                error_types[last_error] += 1
        
        self.log(f"  总 Agent 数: {total_agents}")
        self.log(f"  降级 Agent: {len(degraded_agents)}")
        self.log(f"  阻塞 Agent: {len(blocked_agents)}")
        
        if error_types:
            self.log(f"  常见错误:")
            for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                self.log(f"    - {error}: {count} 次")
        
        insight = {
            "type": "agent_failures",
            "total_agents": total_agents,
            "degraded_count": len(degraded_agents),
            "blocked_count": len(blocked_agents),
            "top_errors": [
                {"error": error, "count": count}
                for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
        }
        
        # 生成建议
        if len(degraded_agents) > total_agents * 0.2:
            insight["recommendation"] = f"超过 20% 的 Agent 处于降级状态，建议检查系统资源或重启"
        elif error_types:
            top_error = max(error_types.items(), key=lambda x: x[1])
            insight["recommendation"] = f"最常见错误: {top_error[0]} ({top_error[1]} 次)，建议针对性修复"
        
        return insight
    
    def analyze_resource_usage(self):
        """分析资源使用趋势"""
        self.log("=== 分析资源使用趋势 ===")
        
        metrics_file = self.workspace / "learning" / "metrics_history.jsonl"
        if not metrics_file.exists():
            self.log("⏭️ 没有历史数据")
            return None
        
        # 读取最近7天的资源数据
        cutoff_date = datetime.now() - timedelta(days=7)
        resource_data = []
        
        with open(metrics_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    metric = json.loads(line)
                    ts = metric.get("ts", "")
                    resource = metric.get("resource", {})
                    
                    if ts and resource:
                        metric_time = datetime.fromisoformat(ts)
                        if metric_time > cutoff_date:
                            resource_data.append({
                                "time": ts,
                                "cpu": resource.get("avg_cpu_percent", 0),
                                "memory": resource.get("avg_memory_percent", 0),
                                "peak_cpu": resource.get("peak_cpu_percent", 0),
                                "peak_memory": resource.get("peak_memory_percent", 0)
                            })
                except:
                    pass
        
        if not resource_data:
            self.log("⏭️ 没有最近7天的资源数据")
            return None
        
        # 计算平均值和峰值
        avg_cpu = sum(d["cpu"] for d in resource_data) / len(resource_data)
        avg_memory = sum(d["memory"] for d in resource_data) / len(resource_data)
        max_cpu = max(d["peak_cpu"] for d in resource_data)
        max_memory = max(d["peak_memory"] for d in resource_data)
        
        self.log(f"  平均 CPU: {avg_cpu:.1f}%")
        self.log(f"  平均内存: {avg_memory:.1f}%")
        self.log(f"  峰值 CPU: {max_cpu:.1f}%")
        self.log(f"  峰值内存: {max_memory:.1f}%")
        
        insight = {
            "type": "resource_usage",
            "avg_cpu": round(avg_cpu, 1),
            "avg_memory": round(avg_memory, 1),
            "max_cpu": round(max_cpu, 1),
            "max_memory": round(max_memory, 1),
            "data_points": len(resource_data)
        }
        
        # 生成建议
        if max_cpu > 90:
            insight["recommendation"] = f"CPU 峰值达到 {max_cpu:.0f}%，建议优化高负载任务或增加资源"
        elif max_memory > 90:
            insight["recommendation"] = f"内存峰值达到 {max_memory:.0f}%，建议清理内存或增加资源"
        elif avg_cpu > 70:
            insight["recommendation"] = f"平均 CPU 使用率 {avg_cpu:.0f}%，建议优化常驻任务"
        
        return insight
    
    def run_daily_analysis(self):
        """每日分析任务"""
        self.log("\n" + "="*50)
        self.log("开始每日分析")
        self.log("="*50)
        
        insights = []
        
        # 1. 分析 Evolution Score
        score_insight = self.analyze_evolution_score()
        if score_insight:
            insights.append(score_insight)
        
        # 2. 分析 Playbook 性能
        playbook_insight = self.analyze_playbook_performance()
        if playbook_insight:
            insights.append(playbook_insight)
        
        # 3. 分析 Agent 失败
        agent_insight = self.analyze_agent_failures()
        if agent_insight:
            insights.append(agent_insight)
        
        # 4. 分析资源使用
        resource_insight = self.analyze_resource_usage()
        if resource_insight:
            insights.append(resource_insight)
        
        # 总结
        self.log("\n=== 分析完成 ===")
        self.log(f"发现 {len(insights)} 个洞察")
        
        # 保存洞察
        insights_file = self.workspace / "analyst_insights.json"
        with open(insights_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "insights": insights
            }, f, indent=2, ensure_ascii=False)
        
        self.log(f"洞察已保存到: {insights_file}")
        
        # 统计建议数量
        recommendations = [i for i in insights if "recommendation" in i]
        
        if recommendations:
            self.log(f"\n生成了 {len(recommendations)} 个优化建议:")
            for i, rec in enumerate(recommendations, 1):
                self.log(f"  {i}. [{rec['type']}] {rec['recommendation']}")
            return f"ANALYSIS_INSIGHTS:{len(insights)}"
        else:
            self.log("无重要发现")
            return "ANALYSIS_OK"

if __name__ == "__main__":
    agent = AIOSAnalystAgent()
    result = agent.run_daily_analysis()
    print(f"\n输出: {result}")
