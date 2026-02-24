#!/usr/bin/env python3
"""
AIOS Agent System - 能力矩阵架构
从"角色式"升级到"能力组合式"
"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass

@dataclass
class Capability:
    """原子能力定义"""
    name: str
    description: str
    tools: List[str]  # 需要的工具权限
    model: str  # 推荐模型
    thinking: str  # thinking 级别
    skills: List[str] = None  # 需要的技能
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []

# 底层能力标签（原子能力）
CAPABILITIES = {
    # 编程类
    "coding": Capability(
        name="coding",
        description="编写代码、实现功能",
        tools=["exec", "read", "write", "edit"],
        model="claude-opus-4-6",
        thinking="medium",
        skills=["coding-agent"]
    ),
    "debugging": Capability(
        name="debugging",
        description="调试代码、定位 bug",
        tools=["exec", "read", "write"],
        model="claude-opus-4-6",
        thinking="high"
    ),
    "testing": Capability(
        name="testing",
        description="编写测试、质量保证",
        tools=["exec", "read", "write", "edit"],
        model="claude-sonnet-4-5",
        thinking="medium"
    ),
    "refactoring": Capability(
        name="refactoring",
        description="重构代码、优化结构",
        tools=["read", "write", "edit"],
        model="claude-opus-4-6",
        thinking="high"
    ),
    
    # 分析类
    "data-analysis": Capability(
        name="data-analysis",
        description="数据分析、统计、可视化",
        tools=["exec", "read", "write"],
        model="claude-sonnet-4-5",
        thinking="low"
    ),
    "profiling": Capability(
        name="profiling",
        description="性能分析、瓶颈定位",
        tools=["exec", "read", "write"],
        model="claude-opus-4-6",
        thinking="high"
    ),
    "monitoring": Capability(
        name="monitoring",
        description="系统监控、健康检查",
        tools=["exec", "read"],
        model="claude-sonnet-4-5",
        thinking="off",
        skills=["system-resource-monitor"]
    ),
    
    # 设计类
    "architecture": Capability(
        name="architecture",
        description="系统设计、架构规划",
        tools=["read", "write", "web_search"],
        model="claude-opus-4-6",
        thinking="high"
    ),
    "design": Capability(
        name="design",
        description="功能设计、接口设计",
        tools=["read", "write"],
        model="claude-opus-4-6",
        thinking="medium"
    ),
    "ui-design": Capability(
        name="ui-design",
        description="UI/UX设计、界面布局、交互设计",
        tools=["read", "write", "web_search", "web_fetch"],
        model="claude-opus-4-6",
        thinking="medium"
    ),
    
    # 审查类
    "code-review": Capability(
        name="code-review",
        description="代码审查、质量检查",
        tools=["read", "write"],
        model="claude-opus-4-6",
        thinking="high"
    ),
    "security-audit": Capability(
        name="security-audit",
        description="安全审计、漏洞检测",
        tools=["read", "write"],
        model="claude-opus-4-6",
        thinking="high"
    ),
    
    # 文档类
    "documentation": Capability(
        name="documentation",
        description="编写文档、API 文档",
        tools=["read", "write", "web_search"],
        model="claude-sonnet-4-5",
        thinking="low"
    ),
    "translation": Capability(
        name="translation",
        description="翻译、国际化",
        tools=["read", "write", "web_search"],
        model="claude-sonnet-4-5",
        thinking="low"
    ),
    
    # 研究类
    "research": Capability(
        name="research",
        description="信息搜索、资料整理",
        tools=["web_search", "web_fetch", "read", "write"],
        model="claude-sonnet-4-5",
        thinking="low"
    ),
    
    # 运维类
    "automation": Capability(
        name="automation",
        description="自动化脚本、批量处理",
        tools=["exec", "read", "write", "edit", "cron"],
        model="claude-sonnet-4-5",
        thinking="low"
    ),
    "deployment": Capability(
        name="deployment",
        description="打包发布、环境配置",
        tools=["exec", "read", "write", "edit"],
        model="claude-sonnet-4-5",
        thinking="medium"
    ),
    "optimization": Capability(
        name="optimization",
        description="性能优化、资源优化",
        tools=["exec", "read", "write"],
        model="claude-opus-4-6",
        thinking="high"
    ),
    
    # 数据工程类
    "data-engineering": Capability(
        name="data-engineering",
        description="数据清洗、ETL 流程",
        tools=["exec", "read", "write", "edit"],
        model="claude-sonnet-4-5",
        thinking="medium"
    ),
    
    # AI 类
    "ml-training": Capability(
        name="ml-training",
        description="机器学习模型训练",
        tools=["exec", "read", "write", "edit", "web_search"],
        model="claude-opus-4-6",
        thinking="high"
    ),
    
    # 游戏开发类
    "game-dev": Capability(
        name="game-dev",
        description="游戏开发、机制设计",
        tools=["exec", "read", "write", "edit", "web_search", "web_fetch"],
        model="claude-opus-4-6",
        thinking="medium",
        skills=["coding-agent"]
    ),
}

# 专业模板（能力组合）
TEMPLATES_V2 = {
    "coder": {
        "name": "代码开发专员",
        "capabilities": ["coding", "debugging", "testing"],
        "description": "负责编写、调试、测试代码"
    },
    "optimizer": {
        "name": "性能优化专员",
        "capabilities": ["coding", "debugging", "profiling", "optimization"],
        "description": "负责性能分析和代码优化"
    },
    "full-stack": {
        "name": "全栈工程师",
        "capabilities": ["coding", "debugging", "testing", "deployment", "monitoring"],
        "description": "负责开发、测试、部署、监控全流程"
    },
    "analyst": {
        "name": "数据分析专员",
        "capabilities": ["data-analysis", "research"],
        "description": "负责数据分析、统计、可视化"
    },
    "monitor": {
        "name": "系统监控专员",
        "capabilities": ["monitoring", "data-analysis"],
        "description": "负责系统健康检查、性能监控"
    },
    "researcher": {
        "name": "信息研究专员",
        "capabilities": ["research", "documentation"],
        "description": "负责信息搜索、整理、总结"
    },
    "architect": {
        "name": "架构师",
        "capabilities": ["architecture", "design", "code-review"],
        "description": "负责系统设计、技术选型、架构评审"
    },
    "reviewer": {
        "name": "代码审查专员",
        "capabilities": ["code-review", "security-audit", "testing"],
        "description": "负责代码审查、质量检查、安全审计"
    },
    "designer": {
        "name": "UI/UX 设计专员",
        "capabilities": ["ui-design", "design", "research"],
        "description": "负责界面设计、交互设计、用户体验优化"
    },
    "debugger": {
        "name": "调试专家",
        "capabilities": ["debugging", "profiling", "code-review"],
        "description": "负责 bug 定位、错误分析、问题诊断"
    },
    "documenter": {
        "name": "文档专员",
        "capabilities": ["documentation", "research"],
        "description": "负责文档编写、API 文档、知识管理"
    },
    "translator": {
        "name": "翻译专员",
        "capabilities": ["translation", "documentation"],
        "description": "负责代码注释翻译、文档多语言、国际化"
    },
    "automation": {
        "name": "自动化专员",
        "capabilities": ["automation", "coding", "testing"],
        "description": "负责自动化脚本、定时任务、批量处理"
    },
    "deployer": {
        "name": "部署专员",
        "capabilities": ["deployment", "automation", "monitoring"],
        "description": "负责打包发布、环境配置、版本管理"
    },
    "data-engineer": {
        "name": "数据工程师",
        "capabilities": ["data-engineering", "coding", "testing"],
        "description": "负责数据清洗、ETL 流程、数据管道"
    },
    "ai-trainer": {
        "name": "AI 训练师",
        "capabilities": ["ml-training", "coding", "data-analysis"],
        "description": "负责机器学习模型训练、优化、评估"
    },
    "game-dev": {
        "name": "游戏开发工程师",
        "capabilities": ["game-dev", "coding", "debugging"],
        "description": "负责游戏开发、机制设计、关卡设计"
    },
    "tester": {
        "name": "测试工程师",
        "capabilities": ["testing", "debugging", "automation"],
        "description": "负责自动化测试、质量保证、bug 验证"
    },
}


class CapabilityMatcher:
    """能力匹配器 - 根据任务需求匹配最佳模板"""
    
    def __init__(self):
        self.capabilities = CAPABILITIES
        self.templates = TEMPLATES_V2
    
    def match_template(self, required_capabilities: List[str]) -> Optional[Dict]:
        """
        根据所需能力匹配最佳模板
        
        Args:
            required_capabilities: 任务需要的能力列表
            
        Returns:
            最佳匹配的模板信息，包含匹配度
        """
        required_set = set(required_capabilities)
        best_match = None
        best_score = 0
        
        for template_id, template in self.templates.items():
            template_caps = set(template["capabilities"])
            
            # 计算匹配度
            intersection = required_set & template_caps
            union = required_set | template_caps
            
            # Jaccard 相似度
            score = len(intersection) / len(union) if union else 0
            
            # 优先选择能力完全覆盖的模板
            if required_set.issubset(template_caps):
                score += 0.5
            
            if score > best_score:
                best_score = score
                best_match = {
                    "template_id": template_id,
                    "template_name": template["name"],
                    "capabilities": template["capabilities"],
                    "match_score": score,
                    "missing_capabilities": list(required_set - template_caps),
                    "extra_capabilities": list(template_caps - required_set)
                }
        
        return best_match
    
    def infer_capabilities_from_task(self, task_description: str) -> List[str]:
        """
        从任务描述推断所需能力
        
        Args:
            task_description: 任务描述文本
            
        Returns:
            推断出的能力列表
        """
        task_lower = task_description.lower()
        inferred = []
        
        # 关键词映射
        keyword_map = {
            "coding": ["编写代码", "实现功能", "开发", "写代码", "code", "implement"],
            "debugging": ["调试", "修复", "bug", "错误", "debug", "fix"],
            "testing": ["测试", "test", "验证", "verify"],
            "data-analysis": ["分析", "统计", "数据", "analyze", "data"],
            "profiling": ["性能分析", "瓶颈", "profile", "performance"],
            "monitoring": ["监控", "检查", "健康", "monitor", "check", "health"],
            "architecture": ["架构", "设计", "architecture", "design"],
            "ui-design": ["UI", "UX", "界面", "交互", "原型", "mockup", "布局", "样式", "配色"],
            "code-review": ["审查", "review", "质量"],
            "documentation": ["文档", "doc", "documentation"],
            "research": ["搜索", "调研", "research", "search"],
            "automation": ["自动化", "脚本", "automation", "script"],
            "deployment": ["部署", "发布", "deploy", "release"],
            "optimization": ["优化", "optimize", "improve"],
            "game-dev": ["游戏", "game"],
        }
        
        for capability, keywords in keyword_map.items():
            if any(kw in task_lower for kw in keywords):
                inferred.append(capability)
        
        return inferred
    
    def get_capability_info(self, capability_name: str) -> Optional[Capability]:
        """获取能力详细信息"""
        return self.capabilities.get(capability_name)
    
    def merge_capabilities(self, capabilities: List[str]) -> Dict:
        """
        合并多个能力的配置
        
        Args:
            capabilities: 能力列表
            
        Returns:
            合并后的配置（工具、模型、thinking）
        """
        tools = set()
        skills = set()
        models = []
        thinking_levels = []
        
        for cap_name in capabilities:
            cap = self.capabilities.get(cap_name)
            if cap:
                tools.update(cap.tools)
                skills.update(cap.skills)
                models.append(cap.model)
                thinking_levels.append(cap.thinking)
        
        # 选择最高级的模型
        model_priority = {"claude-opus-4-6": 2, "claude-sonnet-4-5": 1}
        best_model = max(models, key=lambda m: model_priority.get(m, 0)) if models else "claude-sonnet-4-5"
        
        # 选择最高的 thinking 级别
        thinking_priority = {"high": 3, "medium": 2, "low": 1, "off": 0}
        best_thinking = max(thinking_levels, key=lambda t: thinking_priority.get(t, 0)) if thinking_levels else "low"
        
        return {
            "tools": {
                "allow": list(tools),
                "deny": ["message", "cron", "gateway"]
            },
            "skills": list(skills),
            "model": best_model,
            "thinking": best_thinking
        }


def demo():
    """演示能力匹配"""
    matcher = CapabilityMatcher()
    
    # 测试 1：性能优化任务
    print("=" * 60)
    print("测试 1：性能优化任务")
    task1 = "优化这段代码的性能，找出瓶颈并重构"
    caps1 = matcher.infer_capabilities_from_task(task1)
    print(f"任务: {task1}")
    print(f"推断能力: {caps1}")
    match1 = matcher.match_template(caps1)
    print(f"最佳匹配: {match1['template_name']} (匹配度: {match1['match_score']:.2f})")
    print(f"模板能力: {match1['capabilities']}")
    
    # 测试 2：全栈开发任务
    print("\n" + "=" * 60)
    print("测试 2：全栈开发任务")
    task2 = "开发一个 API，编写测试，部署到生产环境，并监控运行状态"
    caps2 = matcher.infer_capabilities_from_task(task2)
    print(f"任务: {task2}")
    print(f"推断能力: {caps2}")
    match2 = matcher.match_template(caps2)
    print(f"最佳匹配: {match2['template_name']} (匹配度: {match2['match_score']:.2f})")
    print(f"模板能力: {match2['capabilities']}")
    
    # 测试 3：能力合并
    print("\n" + "=" * 60)
    print("测试 3：能力合并")
    caps3 = ["coding", "debugging", "profiling"]
    merged = matcher.merge_capabilities(caps3)
    print(f"能力: {caps3}")
    print(f"合并配置: {merged}")


if __name__ == "__main__":
    demo()
