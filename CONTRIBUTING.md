# Contributing to Self-Improving Loop

感谢你对 Self-Improving Loop 的关注！我们欢迎所有形式的贡献。

## 🤝 如何贡献

### 报告 Bug

如果你发现了 bug，请创建一个 Issue，包含：
- 清晰的标题和描述
- 复现步骤
- 预期行为 vs 实际行为
- 环境信息（Python 版本、操作系统等）
- 相关日志或截图

### 提出新功能

如果你有新功能的想法：
1. 先创建一个 Issue 讨论
2. 说明功能的用途和价值
3. 提供使用示例
4. 等待维护者反馈

### 提交代码

1. **Fork 仓库**
   ```bash
   git clone https://github.com/yourusername/self-improving-loop.git
   cd self-improving-loop
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **编写代码**
   - 遵循现有代码风格
   - 添加必要的测试
   - 更新文档

4. **运行测试**
   ```bash
   pytest
   ```

5. **提交代码**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 清晰描述改动
   - 关联相关 Issue
   - 等待 Code Review

## 📝 代码规范

### Python 风格

- 遵循 PEP 8
- 使用 type hints
- 函数和类添加 docstring
- 变量名使用有意义的英文

### 提交信息

使用 Conventional Commits 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型：**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 重构
- `perf`: 性能优化
- `chore`: 构建/工具相关

**示例：**
```
feat(rollback): add atomic config write

- Use tmp file + rename for atomic writes
- Add config_version to prevent race conditions
- Update tests

Closes #123
```

## 🧪 测试要求

### 新功能必须包含测试

```python
def test_new_feature():
    """测试新功能"""
    loop = SelfImprovingLoop()
    result = loop.new_feature()
    assert result["success"] == True
```

### 测试覆盖率

- 核心功能：100%
- 工具函数：>80%
- 总体：>90%

### 运行测试

```bash
# 所有测试
pytest

# 特定文件
pytest tests/test_core.py

# 覆盖率报告
pytest --cov=self_improving_loop --cov-report=html
```

## 📚 文档要求

### 代码文档

```python
def execute_with_improvement(
    self,
    agent_id: str,
    task: str,
    execute_fn: Callable[[], Any],
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    执行任务并自动触发改进循环

    Args:
        agent_id: Agent ID
        task: 任务描述
        execute_fn: 任务执行函数
        context: 任务上下文（可选）

    Returns:
        {
            "success": bool,
            "improvement_triggered": bool,
            "improvement_applied": int,
            "rollback_executed": Optional[Dict]
        }
    """
```

### 更新文档

如果你的改动影响了用户使用：
- 更新 README.md
- 更新相关文档
- 添加使用示例

## 🔍 Code Review 流程

1. **自动检查**
   - CI 测试必须通过
   - 代码风格检查通过
   - 测试覆盖率达标

2. **人工审查**
   - 至少 1 个维护者 approve
   - 解决所有 review comments
   - 确保文档完整

3. **合并**
   - Squash merge（保持历史清晰）
   - 删除 feature 分支

## 🎯 优先级

### P0（高优先级）
- 安全问题
- 严重 bug
- 性能退化

### P1（中优先级）
- 新功能
- 文档改进
- 测试增强

### P2（低优先级）
- 代码重构
- 工具改进
- 小优化

## 💡 开发建议

### 本地开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 启用 pre-commit hooks
pre-commit install

# 运行格式化
black .
isort .

# 运行 linter
flake8 .
mypy .
```

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 使用 pdb
import pdb; pdb.set_trace()
```

## 🌟 成为维护者

如果你：
- 持续贡献高质量代码
- 积极参与 Issue 和 PR 讨论
- 帮助其他贡献者

我们会邀请你成为维护者！

## 📧 联系

- GitHub Issues: 技术问题
- GitHub Discussions: 一般讨论
- Email: maintainers@example.com

## 🙏 致谢

感谢所有贡献者！你们的贡献让这个项目变得更好。

---

**记住：每个贡献都很重要，无论大小！** ❤️
