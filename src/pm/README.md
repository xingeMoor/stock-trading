# Q脑项目管理系统 (PM Module)

## 📦 模块说明

`src/pm/` 模块提供 Q脑项目的完整管理能力，包括:

- 任务创建与分配
- 里程碑管理
- Agent 工作分配与负载均衡
- 进度跟踪
- 日报/周报自动生成

## 🚀 快速开始

```python
from src.pm import ProjectManager, Priority, TaskType

# 创建项目管理器
pm = ProjectManager("Q脑")

# 注册 Agent
pm.register_agent("agent-001", "开发 Agent", ["dev", "python", "test"])
pm.register_agent("agent-002", "数据 Agent", ["data", "analysis"])

# 创建里程碑
m1 = pm.create_milestone(
    name="M1: 基础架构",
    description="完成系统核心框架",
    planned_start=date(2026, 3, 1),
    planned_end=date(2026, 3, 29)
)

# 创建任务
task = pm.create_task(
    name="数据库设计",
    description="设计数据库 schema",
    priority=Priority.P0,
    task_type=TaskType.DEV,
    estimated_hours=16,
    story_points=8
)

# 添加任务到里程碑
pm.add_task_to_milestone(m1.id, task.id)

# 自动分配任务给最优 Agent
pm.assign_task_to_best_agent(task.id)

# 生成日报
daily_report = pm.generate_daily_report()
print(daily_report.to_markdown())

# 生成周报
weekly_report = pm.generate_weekly_report()
print(weekly_report.to_markdown())

# 获取项目汇总
summary = pm.get_project_summary()
```

## 📋 核心类

### ProjectManager
主项目管理类，提供所有管理功能

**主要方法:**
- `create_task()` - 创建任务
- `create_milestone()` - 创建里程碑
- `register_agent()` - 注册 Agent
- `assign_task_to_best_agent()` - 智能分配任务
- `generate_daily_report()` - 生成日报
- `generate_weekly_report()` - 生成周报
- `get_project_summary()` - 获取项目汇总

### Task
任务数据类

**属性:**
- `id` - 任务 ID (自动生成)
- `name` - 任务名称
- `description` - 任务描述
- `priority` - 优先级 (P0-P3)
- `task_type` - 任务类型 (DEV/TEST/DATA等)
- `status` - 状态 (TODO/IN_PROGRESS/DONE等)
- `estimated_hours` - 估算工时
- `story_points` - 故事点
- `assignee` - 负责人
- `dependencies` - 依赖任务列表

### Milestone
里程碑数据类

**属性:**
- `id` - 里程碑 ID (自动生成，如 M1, M2)
- `name` - 里程碑名称
- `description` - 描述
- `planned_start/end` - 计划开始/结束日期
- `actual_start/end` - 实际开始/结束日期
- `tasks` - 关联任务列表
- `completion_criteria` - 完成标准
- `progress` - 进度百分比

### AgentState
Agent 状态数据类

**属性:**
- `agent_id` - Agent ID
- `name` - Agent 名称
- `status` - 状态 (IDLE/BUSY/OFFLINE)
- `current_tasks` - 当前任务列表
- `max_concurrent` - 最大并发任务数
- `skills` - 技能列表
- `load_score` - 负载分数 (0-100)
- `success_rate` - 任务成功率

### DailyReport / WeeklyReport
日报和周报数据类

**方法:**
- `to_markdown()` - 生成 Markdown 格式报告

## 🎯 优先级定义

| 优先级 | 说明 | 响应时间 |
|--------|------|----------|
| P0 | 关键路径 - 阻塞后续工作 | 立即处理 |
| P1 | 重要任务 - 影响进度 | 24 小时内 |
| P2 | 优化任务 - 提升体验 | 本周内 |
| P3 | 可选任务 - 锦上添花 | 视情况而定 |

## 📊 任务类型

| 类型 | 代码 | 说明 |
|------|------|------|
| 开发 | DEV | 新功能开发、代码实现 |
| 测试 | TEST | 单元测试、集成测试 |
| 数据 | DATA | 数据处理、分析 |
| 交易 | TRADE | 订单执行、调仓 |
| 风控 | RISK | 风险监控、预警 |
| 运维 | OPS | 部署、监控、维护 |
| 文档 | DOC | 文档编写、更新 |
| 审查 | REVIEW | 代码审查、设计评审 |

## ⚖️ 负载均衡算法

Agent 负载分数由三部分组成:

1. **基础负载 (40 分)** - 当前任务数 / 最大并发
2. **时间负载 (30 分)** - 任务已执行时间
3. **表现负载 (30 分)** - 历史成功率

**分配规则:**
- 负载 > 80 的 Agent 不再分配新任务
- 优先分配给技能匹配的 Agent
- 同等条件下选择负载最低的 Agent

## 📁 文件结构

```
src/pm/
├── __init__.py           # 模块导出
├── project_manager.py    # 核心实现
└── README.md            # 本文档
```

## 🔧 配置示例

### 注册 Agent

```python
# 开发 Agent - 最大并发 3 个任务
pm.register_agent(
    agent_id="dev-agent-001",
    name="开发 Agent",
    skills=["dev", "python", "test", "code_review"],
    max_concurrent=3
)

# 数据 Agent - 最大并发 2 个任务
pm.register_agent(
    agent_id="data-agent-001",
    name="数据 Agent",
    skills=["data", "analysis", "pandas", "sql"],
    max_concurrent=2
)

# 风控 Agent - 最大并发 2 个任务
pm.register_agent(
    agent_id="risk-agent-001",
    name="风控 Agent",
    skills=["risk", "monitoring", "alerting"],
    max_concurrent=2
)
```

### 创建任务

```python
# P0 关键任务
task = pm.create_task(
    name="实盘引擎开发",
    description="实现订单执行核心逻辑",
    priority=Priority.P0,
    task_type=TaskType.TRADE,
    estimated_hours=48,
    story_points=13,
    dependencies=["TASK-0001", "TASK-0002"],
    due_date=date(2026, 4, 15),
    tags=["core", "trading"],
    metadata={
        "required_skills": ["trading", "python"],
        "risk_level": "high"
    }
)
```

### 任务状态流转

```python
# 开始任务
pm.update_task_status("TASK-0001", TaskStatus.IN_PROGRESS)

# 任务完成
pm.update_task_status("TASK-0001", TaskStatus.DONE)

# 任务阻塞
pm.update_task_status(
    "TASK-0001",
    TaskStatus.BLOCKED,
    metadata={
        "blocker_impact": "影响后续测试工作",
        "help_needed": "需要数据库权限"
    }
)
```

## 📈 报告示例

### 日报输出

```markdown
# Q 脑项目日报 [2026-03-01]

## ✅ 今日完成
- [TASK-0001] 项目仓库初始化 - agent-001 - 完成
- [TASK-0002] 数据库设计 - agent-001 - 完成

## 🔄 进行中
- [TASK-0003] API 网关开发 - 60% - 预计：2026-03-05
- [TASK-0004] 数据接入模块 - 30% - 预计：2026-03-10

## ⚠️ 阻塞问题
- 无

## 📋 明日计划
- [TASK-0005] 数据清洗模块 - agent-002
- [TASK-0006] 单元测试编写 - agent-001

## 📈 关键指标
- 代码覆盖率：85%
- Bug 数量：2 (新增 0, 修复 1)
- 构建成功率：95%
- 系统可用性：99.9%

## 🔴 风险提醒
- 无
```

## 🧪 测试

```bash
# 运行示例
cd /Users/gexin/.openclaw/workspace
python3 src/pm/project_manager.py
```

## 📝 最佳实践

1. **及时更新任务状态** - 确保进度跟踪准确
2. **合理估算工时** - 使用三点估算法
3. **设置明确的完成标准** - 避免模糊验收
4. **定期生成报告** - 保持信息透明
5. **监控 Agent 负载** - 避免过载或闲置

## 🔗 相关文档

- [PROJECT_PLAN.md](../../docs/PROJECT_PLAN.md) - 项目计划
- [WORKFLOW.md](../../docs/WORKFLOW.md) - 工作流程

---

**维护者:** 小七  
**版本:** 1.0  
**最后更新:** 2026-03-01
