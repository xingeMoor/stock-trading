# Q 脑项目管理系统使用文档

> **版本**: 2.0  
> **作者**: 小七 (Q-Brain)  
> **创建日期**: 2026-03-01  
> **最后更新**: 2026-03-01

---

## 📖 目录

1. [系统概述](#系统概述)
2. [快速开始](#快速开始)
3. [核心模块](#核心模块)
4. [API 参考](#api-参考)
5. [使用示例](#使用示例)
6. [Dashboard 使用](#dashboard-使用)
7. [OpenClaw 集成](#openclaw-集成)

---

## 系统概述

Q 脑项目管理系统 (Project Master V2) 是一套完整的项目管理解决方案，专为量化交易系统开发设计。

### 核心功能

- **项目管理**: 创建、跟踪和管理多个项目
- **任务管理**: 任务创建、分配、优先级排序
- **里程碑管理**: 项目关键节点跟踪
- **任务调度**: 智能 Agent 任务分配与负载均衡
- **验收系统**: 质量评分与验收流程
- **工作流引擎**: 自动化工作流程执行
- **实时 Dashboard**: 可视化项目进度与任务看板

### 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   Dashboard (5008)                   │
│  项目列表 · 任务看板 · 里程碑 · 验收报告              │
└─────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼───────┐  ┌────────▼────────┐
│ ProjectMaster  │  │ TaskScheduler│  │  ReviewSystem   │
│ 项目/任务/里程碑│  │ 任务调度/负载│  │  验收/质量评分   │
└────────────────┘  └──────────────┘  └─────────────────┘
        │
┌───────▼────────┐
│ WorkflowEngine │
│  工作流自动化   │
└────────────────┘
```

---

## 快速开始

### 1. 初始化系统

```python
from src.pm import ProjectMaster, TaskScheduler, ReviewSystem, WorkflowEngine

# 初始化核心模块
pm = ProjectMaster()
scheduler = TaskScheduler(pm)
review_system = ReviewSystem(pm)
workflow_engine = WorkflowEngine(pm)
```

### 2. 创建项目

```python
from datetime import date, timedelta

# 创建新项目
project_id = pm.create_project(
    name="Q 脑系统 V2",
    description="量化交易系统升级",
    start_date=date.today(),
    end_date=date.today() + timedelta(days=90),
    owner="PM"
)
```

### 3. 创建里程碑

```python
# 创建里程碑
m1 = pm.create_milestone(
    project_id=project_id,
    name="M1: 基础架构",
    description="完成系统核心框架",
    planned_start=date.today(),
    planned_end=date.today() + timedelta(days=30),
    completion_criteria=[
        "代码仓库完整",
        "数据库可用",
        "日志可追踪"
    ]
)
```

### 4. 创建任务

```python
# 创建任务
task_id = pm.create_task(
    project_id=project_id,
    name="项目初始化",
    description="创建 Git 仓库和基本结构",
    priority="P0",
    task_type="dev",
    estimated_hours=4,
    story_points=3,
    acceptance_criteria=[
        "仓库创建",
        "目录结构完整",
        "README 编写"
    ]
)

# 关联里程碑
pm.add_task_to_milestone(m1, task_id)
```

### 5. 启动 Dashboard

```bash
# Agent Dashboard (端口 5007)
python agent_dashboard_v2.py

# 项目管理 Dashboard (端口 5008)
python project_dashboard.py
```

---

## 核心模块

### ProjectMaster (项目管理主类)

#### 项目管理

| 方法 | 说明 | 参数 |
|------|------|------|
| `create_project()` | 创建项目 | name, description, start_date, end_date, owner |
| `get_project()` | 获取项目信息 | project_id |
| `get_all_projects()` | 获取所有项目 | status (可选) |
| `update_project_status()` | 更新项目状态 | project_id, status |

#### 任务管理

| 方法 | 说明 | 参数 |
|------|------|------|
| `create_task()` | 创建任务 | project_id, name, priority, task_type, ... |
| `update_task_status()` | 更新任务状态 | task_id, status |
| `assign_task()` | 分配任务 | task_id, assignee |
| `get_task()` | 获取任务信息 | task_id |
| `get_tasks_by_project()` | 获取项目任务 | project_id, status |
| `get_tasks_by_assignee()` | 获取负责人任务 | assignee, status |

#### 里程碑管理

| 方法 | 说明 | 参数 |
|------|------|------|
| `create_milestone()` | 创建里程碑 | project_id, name, planned_start, planned_end |
| `add_task_to_milestone()` | 关联任务 | milestone_id, task_id |
| `get_milestone()` | 获取里程碑 | milestone_id |
| `get_milestones_by_project()` | 获取项目里程碑 | project_id |

#### 工作日志

| 方法 | 说明 | 参数 |
|------|------|------|
| `log_work()` | 记录工作日志 | task_id, message, log_type, agent_id |
| `get_work_logs()` | 获取工作日志 | task_id |

#### 验收系统

| 方法 | 说明 | 参数 |
|------|------|------|
| `create_review()` | 创建验收记录 | task_id, reviewer |
| `complete_review()` | 完成验收 | review_id, status, comments, quality_score |
| `get_reviews_by_task()` | 获取验收记录 | task_id |

---

### TaskScheduler (任务调度器)

#### 核心功能

```python
# 计算任务优先级分数
score = scheduler.calculate_priority_score(task)

# 检查依赖是否满足
if scheduler.check_dependencies(task):
    # 依赖满足，可以执行

# 计算 Agent 负载
load = scheduler.calculate_agent_load('developer')

# 获取可用 Agent
available = scheduler.get_available_agents(required_skills=['python', 'dev'])

# 自动分配任务
assigned_agent = scheduler.assign_task(task_id, auto=True)

# 调度项目任务
scheduled = scheduler.schedule_tasks(project_id, limit=10)

# 获取任务队列
queue = scheduler.get_task_queue(project_id)

# 重新平衡负载
result = scheduler.rebalance_tasks()

# 获取 Agent 利用率
utilization = scheduler.get_agent_utilization()
```

#### 优先级计算规则

| 因素 | 权重 | 说明 |
|------|------|------|
| 优先级 (P0-P3) | 100-25 分 | P0=100, P1=75, P2=50, P3=25 |
| 截止日期 | 0-50 分 | 已延期 +50, 明天 +40, 3 天内 +30 |
| 依赖关系 | +10 分 | 有依赖的任务优先 |
| 故事点 | +5 分 | 大任务 (>8pts) 优先拆分 |

---

### ReviewSystem (验收系统)

#### 验收流程

```python
from src.pm import ReviewStatus

# 创建验收请求
review_id = review_system.create_review_request(
    task_id=task_id,
    reviewer="PM",
    priority="normal"
)

# 检查验收标准
criteria = review_system.check_acceptance_criteria(task_id)

# 执行验收
review_system.evaluate_task(
    review_id=review_id,
    status=ReviewStatus.APPROVED,  # 或 REJECTED, NEEDS_WORK
    comments="完成良好，代码质量高",
    quality_score=9,
    feedback=["代码结构清晰", "文档完整"]
)

# 获取待验收任务
pending = review_system.get_pending_reviews()

# 获取质量指标
metrics = review_system.get_quality_metrics(project_id)

# 生成验收报告
report = review_system.generate_review_report(task_id)
```

#### 验收状态

| 状态 | 说明 | 任务状态变更 |
|------|------|-------------|
| APPROVED | 验收通过 | → done |
| REJECTED | 验收拒绝 | → todo |
| NEEDS_WORK | 需要改进 | → in_progress |

---

### WorkflowEngine (工作流引擎)

#### 预定义工作流

```python
# 标准开发流程
instance_id = workflow_engine.create_development_workflow(
    project_id=project_id,
    task_name="开发新功能"
)

# Bug 修复流程
instance_id = workflow_engine.create_bugfix_workflow(
    project_id=project_id,
    bug_description="登录页面崩溃",
    severity="high"  # high/medium/low
)
```

#### 自定义工作流

```python
# 定义工作流
workflow_engine.define_workflow(
    workflow_id="custom_workflow",
    name="自定义流程",
    description="描述",
    steps=[
        {
            'action': 'create_task',
            'params': {'project_id': '{{project_id}}'},
            'auto_next': True
        },
        {
            'action': 'assign_task',
            'params': {'assignee': 'developer'},
            'auto_next': False
        }
    ]
)

# 启动工作流
instance_id = workflow_engine.start_workflow(
    workflow_id="custom_workflow",
    context={'project_id': project_id}
)

# 获取状态
status = workflow_engine.get_workflow_status(instance_id)

# 暂停/恢复
workflow_engine.pause_workflow(instance_id)
workflow_engine.resume_workflow(instance_id)
```

---

## API 参考

### Agent Dashboard API (5007)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Dashboard 主页 |
| `/api/stats` | GET | 统计数据 |
| `/api/agents` | GET | 所有 Agent |
| `/api/tasks` | GET | 任务列表 |
| `/api/sync` | GET | 同步 OpenClaw 状态 |

### Project Dashboard API (5008)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Dashboard 主页 |
| `/api/dashboard` | GET | Dashboard 数据 |
| `/api/projects` | GET | 项目列表 |
| `/api/tasks` | GET | 任务列表 |
| `/api/milestones` | GET | 里程碑列表 |
| `/api/schedule` | GET | 调度任务 |
| `/api/rebalance` | GET | 重新平衡负载 |

---

## 使用示例

### 示例 1: 完整项目流程

```python
from src.pm import *
from datetime import date, timedelta

# 初始化
pm = ProjectMaster()
scheduler = TaskScheduler(pm)
review_system = ReviewSystem(pm)

# 1. 创建项目
project_id = pm.create_project(
    name="策略回测系统",
    description="多策略回测框架",
    start_date=date.today(),
    end_date=date.today() + timedelta(days=60)
)

# 2. 创建里程碑
m1 = pm.create_milestone(
    project_id=project_id,
    name="M1: 数据层",
    planned_end=date.today() + timedelta(days=20)
)

m2 = pm.create_milestone(
    project_id=project_id,
    name="M2: 回测引擎",
    planned_end=date.today() + timedelta(days=40)
)

# 3. 创建任务
task1 = pm.create_task(
    project_id=project_id,
    name="数据接口设计",
    priority="P0",
    task_type="dev",
    story_points=5
)

task2 = pm.create_task(
    project_id=project_id,
    name="回测引擎核心",
    priority="P0",
    task_type="dev",
    story_points=8,
    dependencies=[task1]
)

# 4. 关联里程碑
pm.add_task_to_milestone(m1, task1)
pm.add_task_to_milestone(m2, task2)

# 5. 调度任务
scheduled = scheduler.schedule_tasks(project_id)

# 6. 记录工作日志
pm.log_work(task1, "开始设计数据接口", agent_id="architect")

# 7. 完成任务后验收
pm.update_task_status(task1, 'review')
review_id = review_system.create_review_request(task1, "PM")
review_system.evaluate_task(
    review_id,
    ReviewStatus.APPROVED,
    quality_score=9
)

# 8. 获取统计
stats = pm.get_project_stats(project_id)
print(f"完成故事点：{stats['completed_story_points']}")
```

### 示例 2: Agent 任务分配

```python
# 获取可用 Agent
available = scheduler.get_available_agents(['python', 'dev'])
print(f"可用 Agent: {available}")

# 分配任务
assigned = scheduler.assign_task(task_id, auto=True)
print(f"分配给：{assigned}")

# 查看负载
utilization = scheduler.get_agent_utilization()
for agent, stats in utilization.items():
    print(f"{agent}: 负载={stats['load_score']:.1f}, 任务={stats['total_tasks']}")

# 重新平衡
result = scheduler.rebalance_tasks()
print(f"重新分配了 {len(result['reassignments'])} 个任务")
```

---

## Dashboard 使用

### Agent Dashboard (5007)

访问 http://localhost:5007

**功能**:
- 实时显示所有 Agent 状态
- 显示使用的模型 (如 bailian/qwen3.5-plus)
- 显示当前任务名称
- 显示运行时长
- 显示最后活跃时间
- 一键同步 OpenClaw 状态

**视图**:
- 统计卡片：各层级 Agent 数量
- Agent 卡片：详细状态信息
- 任务列表：今日任务

### Project Dashboard (5008)

访问 http://localhost:5008

**功能**:
- 项目列表与进度
- 任务看板 (Kanban)
- 里程碑进度
- 验收报告

**视图切换**:
- **总览**: 关键指标与项目一览
- **项目**: 所有项目详情
- **任务看板**: 待办/进行中/验收中/已完成
- **里程碑**: 项目关键节点

---

## OpenClaw 集成

### Agent 状态同步

系统自动与 OpenClaw Subagents 同步状态：

```python
from stock-trading.src.agent_manager import sync_openclaw_agents, get_all_agents

# 手动同步
sync_openclaw_agents()

# 获取 Agent (自动同步)
agents = get_all_agents()

for agent in agents:
    print(f"{agent['name']}: {agent['status']}")
    print(f"  模型：{agent['model']}")
    print(f"  任务：{agent['current_task']}")
    print(f"  时长：{agent['running_duration']}")
```

### 状态映射

| OpenClaw 状态 | 本地状态 | 说明 |
|--------------|---------|------|
| running | running | 运行中 |
| completed | completed | 已完成 |
| error | error | 错误 |
| idle | idle | 空闲 |

---

## 最佳实践

### 1. 任务拆分

- 每个任务故事点建议 3-8 点
- 大任务 (>13 点) 应该拆分为子任务
- 使用依赖关系管理任务顺序

### 2. 优先级设置

- **P0**: 关键路径，立即处理
- **P1**: 重要任务，24 小时内
- **P2**: 优化任务，本周内
- **P3**: 可选任务，视情况而定

### 3. 验收标准

- 在创建任务时定义验收标准
- 验收标准应该具体可衡量
- 验收通过后才能标记为完成

### 4. 工作日志

- 及时记录工作进展
- 记录遇到的问题和解决方案
- 便于后续回顾和总结

### 5. 负载均衡

- 定期检查 Agent 利用率
- 使用 `rebalance_tasks()` 重新分配
- 避免单个 Agent 过载

---

## 故障排查

### Dashboard 无法启动

```bash
# 检查端口占用
lsof -i :5007
lsof -i :5008

# 检查依赖
pip install flask

# 查看日志
python project_dashboard.py 2>&1 | tee dashboard.log
```

### 数据库错误

```bash
# 删除并重建数据库
rm src/pm.db
python -c "from src.pm import init_db; init_db()"
```

### Agent 状态不同步

```python
# 手动同步
from stock-trading.src.agent_manager import sync_openclaw_agents
sync_openclaw_agents()
```

---

## 更新日志

### V2.0 (2026-03-01)

- ✅ 新增 OpenClaw Subagents 实时同步
- ✅ 新增 Agent 模型显示
- ✅ 新增运行时长跟踪
- ✅ 完整项目管理系统
- ✅ 任务调度器与负载均衡
- ✅ 验收系统与质量评分
- ✅ 工作流引擎
- ✅ 全新 Dashboard UI

---

## 联系

- **项目**: Q 脑 (Q-Brain) 量化交易系统
- **作者**: 小七 (AI 助手)
- **Master**: 十一郎

---

*文档由 Q 脑项目管理系统生成*
