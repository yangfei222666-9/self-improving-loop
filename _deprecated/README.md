# 已归档的路由器实现

本目录包含已被 `unified_router_v1.py` 替代的旧路由器实现。

## 归档原因

这些路由器已被统一路由器（Unified Router v1.0）替代，该版本整合了所有功能并提供了更好的生产就绪特性。

## 归档文件

### 1. simple_router.py
- **功能**: 简洁版决策系统，基于 if-elif 决策树
- **归档时间**: 2026-02-24
- **替代方案**: `unified_router_v1.py` 的 simple 模式
- **保留原因**: 参考实现，展示清晰的决策逻辑

### 2. production_router.py
- **功能**: 生产级路由器，包含 4 个护栏（解释性、防抖、预算、失败回退）
- **归档时间**: 2026-02-24
- **替代方案**: `unified_router_v1.py` 的 full 模式
- **保留原因**: 完整的护栏实现参考

### 3. task_router.py
- **功能**: 智能任务路由与决策系统，支持能力匹配
- **归档时间**: 2026-02-24
- **替代方案**: `unified_router_v1.py` + `capabilities.py`
- **保留原因**: 能力匹配逻辑参考

### 4. core/task_router.py → core_task_router.py
- **功能**: 基于规则的任务分类路由器
- **归档时间**: 2026-02-24
- **替代方案**: `unified_router_v1.py`
- **保留原因**: 规则配置方式参考

### 5. unified_router.py
- **功能**: 早期统一路由器实现，支持三档模式（simple/full/auto）
- **归档时间**: 2026-02-24
- **替代方案**: `unified_router_v1.py`
- **保留原因**: 早期架构设计参考

## 迁移指南

如果你的代码仍在使用这些旧路由器，请参考以下迁移方案：

### 从 simple_router 迁移
```python
# 旧代码
from aios.agent_system.simple_router import SimpleRouter
router = SimpleRouter()
decision = router.route(ctx)

# 新代码
from aios.agent_system.unified_router_v1 import UnifiedRouter
router = UnifiedRouter(mode="simple")
plan = router.route(ctx)
```

### 从 production_router 迁移
```python
# 旧代码
from aios.agent_system.production_router import ProductionRouter
router = ProductionRouter()
plan = router.route(ctx)

# 新代码
from aios.agent_system.unified_router_v1 import UnifiedRouter
router = UnifiedRouter(mode="full")
plan = router.route(ctx)
```

### 从 task_router 迁移
```python
# 旧代码
from aios.agent_system.task_router import TaskRouter
router = TaskRouter()
decision = router.route(context)

# 新代码
from aios.agent_system.unified_router_v1 import UnifiedRouter
router = UnifiedRouter(mode="auto")
plan = router.route(context)
```

## 注意事项

1. 这些文件仅供参考，不应在生产代码中使用
2. 如需查看历史实现，请查看 Git 历史记录
3. 统一路由器提供了更好的性能和可维护性
