"""
工作流引擎 - Workflow Engine

功能:
- 定义工作流模板
- 执行工作流
- 状态流转
- 自动化规则

作者：小七
版本：1.0
创建日期：2026-03-01
"""
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging
import json
from .project_master import ProjectMaster, TaskStatus, Priority

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """工作流状态"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 活跃
    PAUSED = "paused"         # 暂停
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败


class WorkflowAction(Enum):
    """工作流动作"""
    CREATE_TASK = "create_task"
    ASSIGN_TASK = "assign_task"
    COMPLETE_TASK = "complete_task"
    TRANSITION = "transition"
    NOTIFY = "notify"
    CREATE_REVIEW = "create_review"
    LOG_PROGRESS = "log_progress"


class WorkflowEngine:
    """
    工作流引擎
    
    功能:
    - 工作流定义与执行
    - 状态机管理
    - 自动化规则
    - 事件驱动
    """

    def __init__(self, project_master: ProjectMaster):
        self.pm = project_master
        self.workflows: Dict[str, Dict] = {}
        self.active_workflows: Dict[str, Dict] = {}
        
        logger.info("WorkflowEngine 初始化完成")

    def define_workflow(
        self,
        workflow_id: str,
        name: str,
        description: str,
        steps: List[Dict],
        triggers: Dict = None
    ):
        """
        定义工作流
        
        Args:
            workflow_id: 工作流 ID
            name: 工作流名称
            description: 描述
            steps: 步骤列表
            triggers: 触发条件
        """
        workflow = {
            'id': workflow_id,
            'name': name,
            'description': description,
            'steps': steps,
            'triggers': triggers or {},
            'state': WorkflowState.DRAFT.value,
            'created_at': datetime.now().isoformat()
        }
        
        self.workflows[workflow_id] = workflow
        logger.info(f"定义工作流：{workflow_id} - {name}")

    def start_workflow(
        self,
        workflow_id: str,
        context: Dict = None
    ) -> str:
        """
        启动工作流
        
        Args:
            workflow_id: 工作流 ID
            context: 上下文数据
            
        Returns:
            str: 实例 ID
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"工作流不存在：{workflow_id}")
        
        instance_id = f"WF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        instance = {
            'instance_id': instance_id,
            'workflow_id': workflow_id,
            'context': context or {},
            'current_step': 0,
            'state': WorkflowState.ACTIVE.value,
            'started_at': datetime.now().isoformat(),
            'history': []
        }
        
        self.active_workflows[instance_id] = instance
        
        logger.info(f"启动工作流实例：{instance_id}")
        
        # 执行第一步
        self._execute_step(instance_id)
        
        return instance_id

    def _execute_step(self, instance_id: str):
        """
        执行工作流步骤
        
        Args:
            instance_id: 实例 ID
        """
        instance = self.active_workflows.get(instance_id)
        if not instance:
            return
        
        workflow = self.workflows.get(instance['workflow_id'])
        if not workflow:
            return
        
        steps = workflow['steps']
        current_step = instance['current_step']
        
        if current_step >= len(steps):
            # 所有步骤完成
            self._complete_workflow(instance_id)
            return
        
        step = steps[current_step]
        action = step.get('action')
        
        logger.info(f"执行步骤 {current_step}: {action}")
        
        # 执行动作
        try:
            if action == WorkflowAction.CREATE_TASK.value:
                self._execute_create_task(instance, step)
            elif action == WorkflowAction.ASSIGN_TASK.value:
                self._execute_assign_task(instance, step)
            elif action == WorkflowAction.COMPLETE_TASK.value:
                self._execute_complete_task(instance, step)
            elif action == WorkflowAction.CREATE_REVIEW.value:
                self._execute_create_review(instance, step)
            elif action == WorkflowAction.TRANSITION.value:
                self._execute_transition(instance, step)
            elif action == WorkflowAction.NOTIFY.value:
                self._execute_notify(instance, step)
            
            # 记录历史
            instance['history'].append({
                'step': current_step,
                'action': action,
                'executed_at': datetime.now().isoformat(),
                'status': 'success'
            })
            
            # 移动到下一步
            instance['current_step'] += 1
            
            # 检查是否需要自动执行下一步
            if step.get('auto_next', True):
                self._execute_step(instance_id)
                
        except Exception as e:
            logger.error(f"步骤执行失败：{e}")
            instance['history'].append({
                'step': current_step,
                'action': action,
                'executed_at': datetime.now().isoformat(),
                'status': 'failed',
                'error': str(e)
            })
            instance['state'] = WorkflowState.FAILED.value

    def _execute_create_task(self, instance: Dict, step: Dict):
        """执行创建任务动作"""
        context = instance['context']
        params = step.get('params', {})
        
        # 从上下文中获取参数
        project_id = params.get('project_id') or context.get('project_id')
        name = params.get('name') or context.get('task_name')
        description = params.get('description', '')
        priority = params.get('priority', 'P2')
        task_type = params.get('task_type', 'dev')
        estimated_hours = params.get('estimated_hours', 0)
        story_points = params.get('story_points', 0)
        assignee = params.get('assignee')
        
        task_id = self.pm.create_task(
            project_id=project_id,
            name=name,
            description=description,
            priority=priority,
            task_type=task_type,
            estimated_hours=estimated_hours,
            story_points=story_points,
            assignee=assignee
        )
        
        # 将任务 ID 保存到上下文
        context['task_id'] = task_id
        instance['context'] = context
        
        logger.info(f"创建任务：{task_id}")

    def _execute_assign_task(self, instance: Dict, step: Dict):
        """执行分配任务动作"""
        context = instance['context']
        params = step.get('params', {})
        
        task_id = params.get('task_id') or context.get('task_id')
        assignee = params.get('assignee')
        
        if task_id and assignee:
            self.pm.assign_task(task_id, assignee)
            logger.info(f"分配任务 {task_id} 给 {assignee}")

    def _execute_complete_task(self, instance: Dict, step: Dict):
        """执行完成任务动作"""
        context = instance['context']
        params = step.get('params', {})
        
        task_id = params.get('task_id') or context.get('task_id')
        
        if task_id:
            self.pm.update_task_status(task_id, 'done')
            logger.info(f"完成任务：{task_id}")

    def _execute_create_review(self, instance: Dict, step: Dict):
        """执行创建验收动作"""
        from .review_system import ReviewSystem
        
        context = instance['context']
        params = step.get('params', {})
        
        task_id = params.get('task_id') or context.get('task_id')
        reviewer = params.get('reviewer', 'PM')
        
        if task_id:
            review_system = ReviewSystem(self.pm)
            review_id = review_system.create_review_request(task_id, reviewer)
            context['review_id'] = review_id
            instance['context'] = context

    def _execute_transition(self, instance: Dict, step: Dict):
        """执行状态转移动作"""
        context = instance['context']
        params = step.get('params', {})
        
        task_id = params.get('task_id') or context.get('task_id')
        new_status = params.get('status')
        
        if task_id and new_status:
            self.pm.update_task_status(task_id, new_status)
            logger.info(f"任务 {task_id} 状态变更为：{new_status}")

    def _execute_notify(self, instance: Dict, step: Dict):
        """执行通知动作"""
        params = step.get('params', {})
        message = params.get('message', '')
        recipients = params.get('recipients', [])
        
        logger.info(f"发送通知：{message} to {recipients}")
        # 实际实现可以集成消息系统

    def _complete_workflow(self, instance_id: str):
        """完成工作流"""
        instance = self.active_workflows.get(instance_id)
        if instance:
            instance['state'] = WorkflowState.COMPLETED.value
            instance['completed_at'] = datetime.now().isoformat()
            logger.info(f"工作流完成：{instance_id}")

    def pause_workflow(self, instance_id: str):
        """暂停工作流"""
        instance = self.active_workflows.get(instance_id)
        if instance:
            instance['state'] = WorkflowState.PAUSED.value
            logger.info(f"工作流暂停：{instance_id}")

    def resume_workflow(self, instance_id: str):
        """恢复工作流"""
        instance = self.active_workflows.get(instance_id)
        if instance and instance['state'] == WorkflowState.PAUSED.value:
            instance['state'] = WorkflowState.ACTIVE.value
            self._execute_step(instance_id)
            logger.info(f"工作流恢复：{instance_id}")

    def get_workflow_status(self, instance_id: str) -> Dict:
        """获取工作流状态"""
        instance = self.active_workflows.get(instance_id)
        if not instance:
            return {'error': '实例不存在'}
        
        workflow = self.workflows.get(instance['workflow_id'])
        
        return {
            'instance_id': instance_id,
            'workflow_name': workflow['name'] if workflow else 'Unknown',
            'state': instance['state'],
            'current_step': instance['current_step'],
            'total_steps': len(workflow['steps']) if workflow else 0,
            'started_at': instance['started_at'],
            'completed_at': instance.get('completed_at'),
            'history': instance['history']
        }

    # ==================== 预定义工作流模板 ====================

    def create_development_workflow(self, project_id: str, task_name: str) -> str:
        """
        创建开发工作流
        
        流程:
        1. 创建任务
        2. 分配给开发者
        3. 执行开发
        4. 创建验收
        5. 完成任务
        """
        workflow_id = "dev_workflow"
        
        # 定义工作流 (如果未定义)
        if workflow_id not in self.workflows:
            self.define_workflow(
                workflow_id=workflow_id,
                name="标准开发流程",
                description="从任务创建到完成的标准开发流程",
                steps=[
                    {
                        'action': WorkflowAction.CREATE_TASK.value,
                        'params': {
                            'project_id': '{{project_id}}',
                            'name': '{{task_name}}',
                            'priority': 'P2',
                            'task_type': 'dev'
                        },
                        'auto_next': True
                    },
                    {
                        'action': WorkflowAction.ASSIGN_TASK.value,
                        'params': {
                            'assignee': 'developer'
                        },
                        'auto_next': True
                    },
                    {
                        'action': WorkflowAction.TRANSITION.value,
                        'params': {
                            'status': 'in_progress'
                        },
                        'auto_next': False  # 等待开发完成
                    },
                    {
                        'action': WorkflowAction.CREATE_REVIEW.value,
                        'params': {
                            'reviewer': 'PM'
                        },
                        'auto_next': False  # 等待验收
                    },
                    {
                        'action': WorkflowAction.COMPLETE_TASK.value,
                        'auto_next': True
                    }
                ]
            )
        
        # 启动工作流
        context = {
            'project_id': project_id,
            'task_name': task_name
        }
        
        instance_id = self.start_workflow(workflow_id, context)
        return instance_id

    def create_bugfix_workflow(self, project_id: str, bug_description: str, severity: str = "medium") -> str:
        """
        创建 Bug 修复工作流
        
        流程:
        1. 创建 Bug 任务 (P0/P1)
        2. 分配给开发者
        3. 修复
        4. 测试验收
        5. 完成
        """
        workflow_id = "bugfix_workflow"
        
        if workflow_id not in self.workflows:
            priority = "P0" if severity == "high" else "P1"
            
            self.define_workflow(
                workflow_id=workflow_id,
                name="Bug 修复流程",
                description="紧急 Bug 修复工作流",
                steps=[
                    {
                        'action': WorkflowAction.CREATE_TASK.value,
                        'params': {
                            'project_id': '{{project_id}}',
                            'name': f"[Bug] {{bug_description}}",
                            'priority': priority,
                            'task_type': 'dev',
                            'metadata': {'is_bug': True, 'severity': severity}
                        },
                        'auto_next': True
                    },
                    {
                        'action': WorkflowAction.ASSIGN_TASK.value,
                        'params': {
                            'assignee': 'developer'
                        },
                        'auto_next': True
                    },
                    {
                        'action': WorkflowAction.TRANSITION.value,
                        'params': {
                            'status': 'in_progress'
                        },
                        'auto_next': False
                    },
                    {
                        'action': WorkflowAction.CREATE_REVIEW.value,
                        'params': {
                            'reviewer': 'tester'
                        },
                        'auto_next': False
                    },
                    {
                        'action': WorkflowAction.COMPLETE_TASK.value,
                        'auto_next': True
                    }
                ]
            )
        
        context = {
            'project_id': project_id,
            'bug_description': bug_description
        }
        
        instance_id = self.start_workflow(workflow_id, context)
        return instance_id


# ==================== 测试函数 ====================

def main():
    """测试函数"""
    pm = ProjectMaster()
    engine = WorkflowEngine(pm)
    
    # 创建测试项目
    project_id = pm.create_project("测试项目", "Workflow Engine 测试")
    
    # 启动开发工作流
    print("\n启动开发工作流...")
    instance_id = engine.create_development_workflow(
        project_id=project_id,
        task_name="开发新功能"
    )
    
    # 获取状态
    status = engine.get_workflow_status(instance_id)
    print(f"\n工作流状态:")
    print(f"  实例：{status['instance_id']}")
    print(f"  流程：{status['workflow_name']}")
    print(f"  状态：{status['state']}")
    print(f"  进度：{status['current_step']}/{status['total_steps']}")
    
    # 启动 Bug 修复工作流
    print("\n启动 Bug 修复工作流...")
    bug_instance = engine.create_bugfix_workflow(
        project_id=project_id,
        bug_description="登录页面崩溃",
        severity="high"
    )
    
    bug_status = engine.get_workflow_status(bug_instance)
    print(f"Bug 修复工作流状态：{bug_status['state']}")


if __name__ == "__main__":
    from .project_master import ProjectMaster
    main()
