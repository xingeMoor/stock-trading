"""
Q 脑项目管理系统 - PM Module

模块:
- project_master: 项目管理主类
- task_scheduler: 任务调度器
- review_system: 验收系统
- workflow_engine: 工作流引擎

使用示例:
    from src.pm import ProjectMaster, TaskScheduler, ReviewSystem, WorkflowEngine
    
    pm = ProjectMaster()
    scheduler = TaskScheduler(pm)
    review = ReviewSystem(pm)
    workflow = WorkflowEngine(pm)
"""

from .project_master import ProjectMaster, Priority, TaskStatus, MilestoneStatus, TaskType, init_db
from .task_scheduler import TaskScheduler
from .review_system import ReviewSystem, ReviewStatus
from .workflow_engine import WorkflowEngine, WorkflowState, WorkflowAction

__all__ = [
    # 主类
    'ProjectMaster',
    'TaskScheduler',
    'ReviewSystem',
    'WorkflowEngine',
    
    # 枚举
    'Priority',
    'TaskStatus',
    'MilestoneStatus',
    'TaskType',
    'ReviewStatus',
    'WorkflowState',
    'WorkflowAction',
    
    # 函数
    'init_db'
]

__version__ = '2.0'
__author__ = '小七 (Q-Brain)'
