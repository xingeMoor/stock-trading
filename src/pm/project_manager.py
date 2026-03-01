"""
Q脑项目管理系统 - Project Manager

负责:
- 项目结构规划
- Agent 工作分配
- 进度跟踪
- 质量评估

作者：小七
版本：1.0
创建日期：2026-03-01
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import json
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================

class Priority(Enum):
    """任务优先级"""
    P0 = 0  # 关键路径 - 立即处理
    P1 = 1  # 重要任务 - 24 小时内
    P2 = 2  # 优化任务 - 本周内
    P3 = 3  # 可选任务 - 视情况而定


class TaskStatus(Enum):
    """任务状态"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class AgentStatus(Enum):
    """Agent 状态"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class TaskType(Enum):
    """任务类型"""
    DEV = "dev"
    TEST = "test"
    DATA = "data"
    TRADE = "trade"
    RISK = "risk"
    OPS = "ops"
    DOC = "doc"
    REVIEW = "review"


class MilestoneStatus(Enum):
    """里程碑状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


# ==================== 数据类定义 ====================

@dataclass
class Task:
    """任务"""
    id: str
    name: str
    description: str
    priority: Priority
    task_type: TaskType
    status: TaskStatus = TaskStatus.TODO
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    story_points: int = 0
    assignee: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[date] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'priority': self.priority.name,
            'task_type': self.task_type.value,
            'status': self.status.value,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'story_points': self.story_points,
            'assignee': self.assignee,
            'dependencies': self.dependencies,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'tags': self.tags,
            'metadata': self.metadata
        }


@dataclass
class Milestone:
    """里程碑"""
    id: str
    name: str
    description: str
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    planned_start: Optional[date] = None
    planned_end: Optional[date] = None
    actual_start: Optional[date] = None
    actual_end: Optional[date] = None
    tasks: List[str] = field(default_factory=list)  # Task IDs
    completion_criteria: List[str] = field(default_factory=list)
    progress: float = 0.0  # 0-100

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'planned_start': self.planned_start.isoformat() if self.planned_start else None,
            'planned_end': self.planned_end.isoformat() if self.planned_end else None,
            'actual_start': self.actual_start.isoformat() if self.actual_start else None,
            'actual_end': self.actual_end.isoformat() if self.actual_end else None,
            'tasks': self.tasks,
            'completion_criteria': self.completion_criteria,
            'progress': self.progress
        }


@dataclass
class AgentState:
    """Agent 状态"""
    agent_id: str
    name: str
    status: AgentStatus = AgentStatus.IDLE
    current_tasks: List[str] = field(default_factory=list)  # Task IDs
    max_concurrent: int = 3
    skills: List[str] = field(default_factory=list)
    load_score: float = 0.0
    avg_task_time: float = 0.0
    success_rate: float = 1.0
    completed_tasks: int = 0
    failed_tasks: int = 0
    last_active: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status.value,
            'current_tasks': self.current_tasks,
            'max_concurrent': self.max_concurrent,
            'skills': self.skills,
            'load_score': self.load_score,
            'avg_task_time': self.avg_task_time,
            'success_rate': self.success_rate,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'last_active': self.last_active.isoformat()
        }


@dataclass
class DailyReport:
    """日报"""
    date: date
    completed_tasks: List[Dict] = field(default_factory=list)
    in_progress_tasks: List[Dict] = field(default_factory=list)
    blocked_issues: List[Dict] = field(default_factory=list)
    tomorrow_plan: List[Dict] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    risks: List[Dict] = field(default_factory=list)

    def to_markdown(self) -> str:
        """生成 Markdown 格式日报"""
        lines = [
            f"# Q 脑项目日报 [{self.date.isoformat()}]",
            "",
            "## ✅ 今日完成",
        ]
        
        for task in self.completed_tasks:
            lines.append(f"- [{task.get('id', '')}] {task.get('name', '')} - {task.get('assignee', '')} - 完成")
        
        if not self.completed_tasks:
            lines.append("- 无")
        
        lines.extend([
            "",
            "## 🔄 进行中",
        ])
        
        for task in self.in_progress_tasks:
            progress = task.get('progress', 0)
            eta = task.get('eta', 'TBD')
            lines.append(f"- [{task.get('id', '')}] {task.get('name', '')} - {progress}% - 预计：{eta}")
        
        if not self.in_progress_tasks:
            lines.append("- 无")
        
        lines.extend([
            "",
            "## ⚠️ 阻塞问题",
        ])
        
        for issue in self.blocked_issues:
            lines.append(f"- {issue.get('description', '')} - 影响：{issue.get('impact', '')} - 需要：{issue.get('help_needed', '')}")
        
        if not self.blocked_issues:
            lines.append("- 无")
        
        lines.extend([
            "",
            "## 📋 明日计划",
        ])
        
        for task in self.tomorrow_plan:
            lines.append(f"- [{task.get('id', '')}] {task.get('name', '')} - {task.get('assignee', '')}")
        
        if not self.tomorrow_plan:
            lines.append("- 无")
        
        lines.extend([
            "",
            "## 📈 关键指标",
        ])
        
        for key, value in self.metrics.items():
            lines.append(f"- {key}: {value}")
        
        lines.extend([
            "",
            "## 🔴 风险提醒",
        ])
        
        for risk in self.risks:
            lines.append(f"- {risk.get('description', '')} - 等级：{risk.get('level', '')} - 措施：{risk.get('action', '')}")
        
        if not self.risks:
            lines.append("- 无")
        
        return "\n".join(lines)


@dataclass
class WeeklyReport:
    """周报"""
    start_date: date
    end_date: date
    summary: str = ""
    milestone_progress: List[Dict] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    issues_risks: List[Dict] = field(default_factory=list)
    next_week_plan: List[Dict] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    total_story_points: int = 0
    completed_story_points: int = 0
    total_hours: float = 0.0

    def to_markdown(self) -> str:
        """生成 Markdown 格式周报"""
        lines = [
            f"# Q 脑项目周报 [{self.start_date.isoformat()} ~ {self.end_date.isoformat()}]",
            "",
            "## 📌 本周摘要",
            f"本周整体进度：{self.summary}",
            f"完成故事点：{self.completed_story_points} 点 (总：{self.total_story_points})",
            f"投入工时：{self.total_hours:.1f} 人天",
            "",
            "## 🎯 里程碑进展",
            "| 里程碑 | 计划完成 | 预计完成 | 进度 | 状态 |",
            "|--------|----------|----------|------|------|",
        ]
        
        for m in self.milestone_progress:
            status_icon = "🟢" if m.get('status') == 'on_track' else "🟡" if m.get('status') == 'at_risk' else "🔴"
            lines.append(
                f"| {m.get('name', '')} | {m.get('planned_end', '')} | {m.get('expected_end', '')} | "
                f"{m.get('progress', 0)}% | {status_icon} |"
            )
        
        lines.extend([
            "",
            "## ✨ 关键成果",
        ])
        
        for i, achievement in enumerate(self.achievements, 1):
            lines.append(f"{i}. {achievement}")
        
        if not self.achievements:
            lines.append("- 无")
        
        lines.extend([
            "",
            "## ⚠️ 问题与风险",
            "| 问题/风险 | 等级 | 影响 | 应对措施 | 负责人 |",
            "|-----------|------|------|----------|--------|",
        ])
        
        for item in self.issues_risks:
            lines.append(
                f"| {item.get('description', '')} | {item.get('level', '')} | "
                f"{item.get('impact', '')} | {item.get('action', '')} | {item.get('owner', '')} |"
            )
        
        if not self.issues_risks:
            lines.append("| - | - | - | - | - |")
        
        lines.extend([
            "",
            "## 📋 下周计划",
        ])
        
        for task in self.next_week_plan:
            priority = task.get('priority', 'P2')
            lines.append(f"- [{priority}] {task.get('description', '')} - {task.get('assignee', '')}")
        
        if not self.next_week_plan:
            lines.append("- 无")
        
        lines.extend([
            "",
            "## 📊 资源情况",
        ])
        
        for key, value in self.resources.items():
            lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)


# ==================== 项目管理器 ====================

class ProjectManager:
    """
    Q脑项目管理系统
    
    功能:
    - 任务和里程碑管理
    - Agent 工作分配与负载均衡
    - 进度跟踪与报告生成
    - 质量评估
    """

    def __init__(self, project_name: str = "Q脑"):
        self.project_name = project_name
        self.tasks: Dict[str, Task] = {}
        self.milestones: Dict[str, Milestone] = {}
        self.agents: Dict[str, AgentState] = {}
        self.daily_reports: Dict[date, DailyReport] = {}
        self.weekly_reports: List[WeeklyReport] = []
        
        logger.info(f"ProjectManager 初始化完成：{project_name}")

    # ==================== 任务管理 ====================

    def create_task(
        self,
        name: str,
        description: str,
        priority: Priority,
        task_type: TaskType,
        estimated_hours: float = 0.0,
        story_points: int = 0,
        dependencies: List[str] = None,
        due_date: Optional[date] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Task:
        """创建新任务"""
        task_id = f"TASK-{len(self.tasks) + 1:04d}"
        
        task = Task(
            id=task_id,
            name=name,
            description=description,
            priority=priority,
            task_type=task_type,
            estimated_hours=estimated_hours,
            story_points=story_points,
            dependencies=dependencies or [],
            due_date=due_date,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task
        logger.info(f"创建任务：{task_id} - {name}")
        
        return task

    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs):
        """更新任务状态"""
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在：{task_id}")
        
        task = self.tasks[task_id]
        old_status = task.status
        task.status = status
        
        # 状态变更时的额外处理
        if status == TaskStatus.IN_PROGRESS and old_status == TaskStatus.TODO:
            task.started_at = datetime.now()
        
        elif status == TaskStatus.DONE:
            task.completed_at = datetime.now()
            # 更新实际工时
            if task.started_at:
                task.actual_hours = (task.completed_at - task.started_at).total_seconds() / 3600
        
        # 应用其他更新
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        logger.info(f"任务 {task_id} 状态变更：{old_status.value} -> {status.value}")
        
        # 更新关联的里程碑进度
        self._update_milestone_progress(task)

    def assign_task(self, task_id: str, agent_id: str):
        """分配任务给 Agent"""
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在：{task_id}")
        if agent_id not in self.agents:
            raise ValueError(f"Agent 不存在：{agent_id}")
        
        task = self.tasks[task_id]
        agent = self.agents[agent_id]
        
        # 检查依赖
        if not self._check_dependencies(task):
            raise ValueError(f"任务 {task_id} 的依赖未完成")
        
        # 检查 Agent 负载
        if agent.load_score >= 80:
            logger.warning(f"Agent {agent_id} 负载过高 ({agent.load_score})")
        
        # 分配任务
        task.assignee = agent_id
        agent.current_tasks.append(task_id)
        agent.last_active = datetime.now()
        
        # 更新任务状态
        if task.status == TaskStatus.TODO:
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()
        
        logger.info(f"任务 {task_id} 分配给 Agent {agent_id}")

    def _check_dependencies(self, task: Task) -> bool:
        """检查任务依赖是否满足"""
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                return False
            if self.tasks[dep_id].status != TaskStatus.DONE:
                return False
        return True

    def _update_milestone_progress(self, task: Task):
        """更新关联里程碑的进度"""
        for milestone in self.milestones.values():
            if task.id in milestone.tasks:
                # 计算里程碑进度
                completed = sum(
                    1 for tid in milestone.tasks
                    if tid in self.tasks and self.tasks[tid].status == TaskStatus.DONE
                )
                milestone.progress = (completed / len(milestone.tasks)) * 100 if milestone.tasks else 0
                
                if milestone.progress == 100:
                    milestone.status = MilestoneStatus.COMPLETED
                    milestone.actual_end = date.today()
                elif milestone.progress > 0:
                    milestone.status = MilestoneStatus.IN_PROGRESS
                    if not milestone.actual_start:
                        milestone.actual_start = date.today()

    # ==================== 里程碑管理 ====================

    def create_milestone(
        self,
        name: str,
        description: str,
        planned_start: Optional[date] = None,
        planned_end: Optional[date] = None,
        completion_criteria: List[str] = None
    ) -> Milestone:
        """创建里程碑"""
        milestone_id = f"M{len(self.milestones) + 1}"
        
        milestone = Milestone(
            id=milestone_id,
            name=name,
            description=description,
            planned_start=planned_start,
            planned_end=planned_end,
            completion_criteria=completion_criteria or []
        )
        
        self.milestones[milestone_id] = milestone
        logger.info(f"创建里程碑：{milestone_id} - {name}")
        
        return milestone

    def add_task_to_milestone(self, milestone_id: str, task_id: str):
        """添加任务到里程碑"""
        if milestone_id not in self.milestones:
            raise ValueError(f"里程碑不存在：{milestone_id}")
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在：{task_id}")
        
        self.milestones[milestone_id].tasks.append(task_id)
        logger.info(f"任务 {task_id} 添加到里程碑 {milestone_id}")

    # ==================== Agent 管理 ====================

    def register_agent(
        self,
        agent_id: str,
        name: str,
        skills: List[str],
        max_concurrent: int = 3
    ) -> AgentState:
        """注册 Agent"""
        agent = AgentState(
            agent_id=agent_id,
            name=name,
            skills=skills,
            max_concurrent=max_concurrent
        )
        
        self.agents[agent_id] = agent
        logger.info(f"注册 Agent：{agent_id} - {name}")
        
        return agent

    def calculate_agent_load(self, agent_id: str) -> float:
        """计算 Agent 负载分数"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent 不存在：{agent_id}")
        
        agent = self.agents[agent_id]
        
        # 基础负载 (40 分)
        base_load = (len(agent.current_tasks) / agent.max_concurrent) * 40 if agent.max_concurrent > 0 else 100
        
        # 时间负载 (30 分) - 基于当前任务已执行时间
        time_load = 0
        for task_id in agent.current_tasks:
            if task_id in self.tasks and self.tasks[task_id].started_at:
                elapsed = (datetime.now() - self.tasks[task_id].started_at).total_seconds() / 60
                time_load += min(10, elapsed / 60)  # 每小时增加 1 分，最多 10 分 per task
        time_load = min(30, time_load)
        
        # 历史表现负载 (30 分)
        total_tasks = agent.completed_tasks + agent.failed_tasks
        if total_tasks > 0:
            performance_load = (1 - agent.success_rate) * 30
        else:
            performance_load = 0
        
        agent.load_score = base_load + time_load + performance_load
        agent.last_active = datetime.now()
        
        return agent.load_score

    def assign_task_to_best_agent(self, task_id: str) -> Optional[str]:
        """为任务分配最优 Agent"""
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在：{task_id}")
        
        task = self.tasks[task_id]
        
        # 计算所有 Agent 的负载
        available_agents = []
        for agent_id, agent in self.agents.items():
            if agent.status == AgentStatus.OFFLINE:
                continue
            if agent.load_score >= 80:
                continue
            
            # 检查技能匹配
            required_skills = task.metadata.get('required_skills', [])
            if required_skills and not any(skill in agent.skills for skill in required_skills):
                continue
            
            self.calculate_agent_load(agent_id)
            
            if agent.load_score < 80:
                available_agents.append(agent)
        
        if not available_agents:
            logger.warning(f"没有可用的 Agent 分配给任务 {task_id}")
            return None
        
        # 按负载分数排序
        available_agents.sort(key=lambda a: a.load_score)
        
        # 考虑亲和性 (相同类型任务优先)
        for agent in available_agents:
            if task.task_type.value in agent.skills:
                self.assign_task(task_id, agent.agent_id)
                return agent.agent_id
        
        # 分配给负载最低的 Agent
        best_agent = available_agents[0]
        self.assign_task(task_id, best_agent.agent_id)
        
        return best_agent.agent_id

    # ==================== 报告生成 ====================

    def generate_daily_report(self, report_date: Optional[date] = None) -> DailyReport:
        """生成日报"""
        if report_date is None:
            report_date = date.today()
        
        report = DailyReport(date=report_date)
        
        # 收集今日完成的任务
        for task in self.tasks.values():
            if task.completed_at and task.completed_at.date() == report_date:
                report.completed_tasks.append({
                    'id': task.id,
                    'name': task.name,
                    'assignee': task.assignee,
                    'priority': task.priority.name,
                    'actual_hours': task.actual_hours
                })
            
            elif task.status == TaskStatus.IN_PROGRESS:
                # 进行中的任务
                progress = self._calculate_task_progress(task)
                eta = self._estimate_task_eta(task)
                report.in_progress_tasks.append({
                    'id': task.id,
                    'name': task.name,
                    'assignee': task.assignee,
                    'progress': progress,
                    'eta': eta
                })
            
            elif task.status == TaskStatus.BLOCKED:
                report.blocked_issues.append({
                    'id': task.id,
                    'name': task.name,
                    'description': f"任务 {task.id} 被阻塞",
                    'impact': task.metadata.get('blocker_impact', '未知'),
                    'help_needed': task.metadata.get('help_needed', '未知')
                })
        
        # 明日计划 (未开始的高优先级任务)
        tomorrow_tasks = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.TODO
            and task.priority in [Priority.P0, Priority.P1]
            and (not task.due_date or task.due_date > report_date)
        ][:5]  # 最多 5 个
        
        for task in tomorrow_tasks:
            report.tomorrow_plan.append({
                'id': task.id,
                'name': task.name,
                'assignee': task.assignee or '未分配',
                'priority': task.priority.name
            })
        
        # 关键指标
        report.metrics = {
            '代码覆盖率': f"{self._get_code_coverage()}%",
            'Bug 数量': f"{self._get_bug_count()} (新增 {self._get_new_bugs_today(report_date)}, 修复 {self._get_fixed_bugs_today(report_date)})",
            '构建成功率': f"{self._get_build_success_rate()}%",
            '系统可用性': f"{self._get_system_availability()}%"
        }
        
        # 风险
        report.risks = self._get_current_risks()
        
        self.daily_reports[report_date] = report
        logger.info(f"生成日报：{report_date}")
        
        return report

    def generate_weekly_report(self, start_date: Optional[date] = None) -> WeeklyReport:
        """生成周报"""
        if start_date is None:
            # 默认从本周一开始
            today = date.today()
            start_date = today - timedelta(days=today.weekday())
        
        end_date = start_date + timedelta(days=6)
        
        report = WeeklyReport(
            start_date=start_date,
            end_date=end_date
        )
        
        # 汇总本周数据
        total_sp = 0
        completed_sp = 0
        total_hours = 0.0
        
        for task in self.tasks.values():
            if task.story_points > 0:
                total_sp += task.story_points
                if task.status == TaskStatus.DONE:
                    completed_sp += task.story_points
            
            if task.actual_hours > 0:
                total_hours += task.actual_hours
        
        report.total_story_points = total_sp
        report.completed_story_points = completed_sp
        report.total_hours = total_hours / 8  # 转换为天
        
        # 整体进度摘要
        progress_rate = (completed_sp / total_sp * 100) if total_sp > 0 else 0
        report.summary = f"{progress_rate:.1f}% (↑{self._get_weekly_progress_change(start_date):.1f}%)"
        
        # 里程碑进展
        for milestone in self.milestones.values():
            status = 'on_track'
            if milestone.planned_end and milestone.actual_end:
                if milestone.actual_end > milestone.planned_end:
                    status = 'delayed'
            elif milestone.planned_end and date.today() > milestone.planned_end and milestone.progress < 100:
                status = 'at_risk'
            
            report.milestone_progress.append({
                'name': milestone.name,
                'planned_end': milestone.planned_end.isoformat() if milestone.planned_end else 'TBD',
                'expected_end': milestone.actual_end.isoformat() if milestone.actual_end else 'TBD',
                'progress': milestone.progress,
                'status': status
            })
        
        # 本周完成的里程碑
        for milestone in self.milestones.values():
            if milestone.actual_end and start_date <= milestone.actual_end <= end_date:
                report.achievements.append(f"完成里程碑：{milestone.name}")
        
        # 本周完成的重要任务
        completed_tasks = [
            task for task in self.tasks.values()
            if task.completed_at and start_date <= task.completed_at.date() <= end_date
            and task.priority in [Priority.P0, Priority.P1]
        ]
        
        for task in completed_tasks[:5]:
            report.achievements.append(f"完成任务：{task.name}")
        
        # 问题与风险
        report.issues_risks = self._get_current_risks()
        
        # 下周计划
        next_week_tasks = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.TODO
            and task.priority in [Priority.P0, Priority.P1]
        ][:10]
        
        for task in next_week_tasks:
            report.next_week_plan.append({
                'priority': task.priority.name,
                'description': task.name,
                'assignee': task.assignee or '未分配'
            })
        
        # 资源情况
        report.resources = {
            '人力投入': f"{total_hours / 8:.1f} 人天 (可用：{len(self.agents) * 5 * 8 / 8:.1f} 人天)",
            'Agent 在线': f"{sum(1 for a in self.agents.values() if a.status != AgentStatus.OFFLINE)}/{len(self.agents)}",
            '任务完成率': f"{completed_sp / total_sp * 100:.1f}%" if total_sp > 0 else 'N/A'
        }
        
        self.weekly_reports.append(report)
        logger.info(f"生成周报：{start_date} ~ {end_date}")
        
        return report

    def _calculate_task_progress(self, task: Task) -> int:
        """估算任务进度"""
        if task.status == TaskStatus.DONE:
            return 100
        if task.status == TaskStatus.TODO:
            return 0
        
        # 基于已用时间和估算时间
        if task.started_at and task.estimated_hours > 0:
            elapsed = (datetime.now() - task.started_at).total_seconds() / 3600
            progress = min(90, int((elapsed / task.estimated_hours) * 100))
            return progress
        
        return 50  # 默认

    def _estimate_task_eta(self, task: Task) -> str:
        """估算任务完成时间"""
        if task.due_date:
            return task.due_date.isoformat()
        
        if task.started_at and task.estimated_hours > 0:
            elapsed = (datetime.now() - task.started_at).total_seconds() / 3600
            remaining = max(0, task.estimated_hours - elapsed)
            eta = datetime.now() + timedelta(hours=remaining)
            return eta.strftime('%Y-%m-%d')
        
        return "TBD"

    def _get_code_coverage(self) -> int:
        """获取代码覆盖率 (占位实现)"""
        return 85

    def _get_bug_count(self) -> int:
        """获取 Bug 数量 (占位实现)"""
        return sum(1 for t in self.tasks.values() if 'bug' in t.tags)

    def _get_new_bugs_today(self, report_date: date) -> int:
        """获取今日新增 Bug 数"""
        return sum(
            1 for t in self.tasks.values()
            if 'bug' in t.tags and t.created_at.date() == report_date
        )

    def _get_fixed_bugs_today(self, report_date: date) -> int:
        """获取今日修复 Bug 数"""
        return sum(
            1 for t in self.tasks.values()
            if 'bug' in t.tags and t.completed_at and t.completed_at.date() == report_date
        )

    def _get_build_success_rate(self) -> int:
        """获取构建成功率 (占位实现)"""
        return 95

    def _get_system_availability(self) -> str:
        """获取系统可用性 (占位实现)"""
        return "99.9"

    def _get_current_risks(self) -> List[Dict]:
        """获取当前风险"""
        risks = []
        
        # 检查延期风险
        for task in self.tasks.values():
            if task.due_date and task.status != TaskStatus.DONE:
                if date.today() > task.due_date:
                    risks.append({
                        'description': f"任务 {task.id} 已延期",
                        'level': '高' if task.priority == Priority.P0 else '中',
                        'impact': task.metadata.get('delay_impact', '影响项目进度'),
                        'action': '立即处理',
                        'owner': task.assignee or '未分配'
                    })
        
        # 检查 Agent 负载风险
        for agent in self.agents.values():
            if agent.load_score > 80:
                risks.append({
                    'description': f"Agent {agent.name} 负载过高 ({agent.load_score:.1f})",
                    'level': '中',
                    'impact': '可能影响任务执行效率',
                    'action': '考虑任务重新分配或增加资源',
                    'owner': 'PM'
                })
        
        return risks

    def _get_weekly_progress_change(self, start_date: date) -> float:
        """获取周进度变化"""
        # 简化实现，返回固定值
        return 5.0

    # ==================== 数据持久化 ====================

    def save_to_file(self, filepath: str):
        """保存项目状态到文件"""
        data = {
            'project_name': self.project_name,
            'tasks': {k: v.to_dict() for k, v in self.tasks.items()},
            'milestones': {k: v.to_dict() for k, v in self.milestones.items()},
            'agents': {k: v.to_dict() for k, v in self.agents.items()},
            'last_updated': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"项目状态保存到：{filepath}")

    def load_from_file(self, filepath: str):
        """从文件加载项目状态"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 恢复数据 (简化实现)
        logger.info(f"项目状态从 {filepath} 加载")
        
        return data

    # ==================== 查询方法 ====================

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态获取任务"""
        return [t for t in self.tasks.values() if t.status == status]

    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        """按优先级获取任务"""
        return [t for t in self.tasks.values() if t.priority == priority]

    def get_tasks_by_assignee(self, assignee: str) -> List[Task]:
        """按负责人获取任务"""
        return [t for t in self.tasks.values() if t.assignee == assignee]

    def get_blocked_tasks(self) -> List[Task]:
        """获取被阻塞的任务"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.BLOCKED]

    def get_milestone_summary(self) -> Dict:
        """获取里程碑汇总"""
        summary = {
            'total': len(self.milestones),
            'completed': sum(1 for m in self.milestones.values() if m.status == MilestoneStatus.COMPLETED),
            'in_progress': sum(1 for m in self.milestones.values() if m.status == MilestoneStatus.IN_PROGRESS),
            'not_started': sum(1 for m in self.milestones.values() if m.status == MilestoneStatus.NOT_STARTED),
            'delayed': sum(1 for m in self.milestones.values() if m.status == MilestoneStatus.DELAYED)
        }
        summary['overall_progress'] = (
            sum(m.progress for m in self.milestones.values()) / len(self.milestones)
            if self.milestones else 0
        )
        return summary

    def get_project_summary(self) -> Dict:
        """获取项目汇总"""
        return {
            'project_name': self.project_name,
            'total_tasks': len(self.tasks),
            'tasks_by_status': {
                status.value: len(self.get_tasks_by_status(status))
                for status in TaskStatus
            },
            'tasks_by_priority': {
                priority.name: len(self.get_tasks_by_priority(priority))
                for priority in Priority
            },
            'total_agents': len(self.agents),
            'active_agents': sum(1 for a in self.agents.values() if a.status != AgentStatus.OFFLINE),
            'milestones': self.get_milestone_summary(),
            'last_updated': datetime.now().isoformat()
        }


# ==================== 主函数示例 ====================

def main():
    """示例：初始化项目管理系统"""
    # 创建项目管理器
    pm = ProjectManager("Q脑")
    
    # 注册 Agent
    pm.register_agent("agent-001", "开发 Agent", ["dev", "test", "python"], max_concurrent=3)
    pm.register_agent("agent-002", "数据 Agent", ["data", "analysis", "python"], max_concurrent=2)
    pm.register_agent("agent-003", "风控 Agent", ["risk", "analysis", "monitoring"], max_concurrent=2)
    
    # 创建里程碑
    m1 = pm.create_milestone(
        name="M1: 基础架构搭建",
        description="完成系统核心框架和基础设施",
        planned_start=date(2026, 3, 1),
        planned_end=date(2026, 3, 29),
        completion_criteria=[
            "代码仓库结构完整",
            "数据库可正常读写",
            "基础数据可获取",
            "系统日志可追踪"
        ]
    )
    
    # 创建任务
    task1 = pm.create_task(
        name="项目仓库初始化",
        description="创建 Git 仓库，设置基本结构",
        priority=Priority.P0,
        task_type=TaskType.DEV,
        estimated_hours=2,
        story_points=2,
        tags=["setup", "infrastructure"]
    )
    
    task2 = pm.create_task(
        name="数据库设计与搭建",
        description="设计数据库 schema，搭建数据库服务",
        priority=Priority.P0,
        task_type=TaskType.DEV,
        estimated_hours=16,
        story_points=8,
        dependencies=[task1.id],
        tags=["database", "infrastructure"]
    )
    
    # 添加任务到里程碑
    pm.add_task_to_milestone(m1.id, task1.id)
    pm.add_task_to_milestone(m1.id, task2.id)
    
    # 分配任务
    pm.assign_task_to_best_agent(task1.id)
    
    # 生成报告
    daily_report = pm.generate_daily_report()
    print("\n=== 今日日报 ===")
    print(daily_report.to_markdown())
    
    weekly_report = pm.generate_weekly_report()
    print("\n=== 本周周报 ===")
    print(weekly_report.to_markdown())
    
    # 项目汇总
    print("\n=== 项目汇总 ===")
    summary = pm.get_project_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    return pm


if __name__ == "__main__":
    main()
