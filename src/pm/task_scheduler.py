"""
任务调度器 - Task Scheduler

功能:
- 任务优先级排序
- Agent 负载均衡
- 任务分配策略
- 依赖管理

作者：小七
版本：1.0
创建日期：2026-03-01
"""
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import logging
from .project_master import ProjectMaster, Priority, TaskStatus

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    任务调度器
    
    功能:
    - 智能任务分配
    - 负载均衡
    - 优先级调度
    - 依赖检查
    """

    def __init__(self, project_master: ProjectMaster):
        self.pm = project_master
        self.agent_load: Dict[str, float] = {}  # Agent 负载分数
        self.agent_tasks: Dict[str, List[str]] = {}  # Agent 当前任务
        
        logger.info("TaskScheduler 初始化完成")

    def calculate_priority_score(self, task: Dict) -> float:
        """
        计算任务优先级分数
        
        分数越高，优先级越高
        
        考虑因素:
        - 优先级 (P0-P3)
        - 截止日期
        - 依赖关系
        - 故事点
        """
        score = 0.0
        
        # 基础优先级分数
        priority_scores = {
            'P0': 100,
            'P1': 75,
            'P2': 50,
            'P3': 25
        }
        score += priority_scores.get(task.get('priority', 'P2'), 50)
        
        # 截止日期加分
        due_date = task.get('due_date')
        if due_date:
            try:
                due = datetime.fromisoformat(due_date).date()
                days_left = (due - date.today()).days
                
                if days_left < 0:
                    score += 50  # 已延期
                elif days_left <= 1:
                    score += 40  # 明天到期
                elif days_left <= 3:
                    score += 30  # 3 天内
                elif days_left <= 7:
                    score += 20  # 一周内
            except Exception:
                pass
        
        # 依赖关系加分 (有依赖的任务优先)
        dependencies = task.get('dependencies', [])
        if dependencies:
            score += 10
        
        # 故事点 (大任务优先拆分)
        story_points = task.get('story_points', 0)
        if story_points > 8:
            score += 5  # 大任务需要尽早开始
        
        return score

    def check_dependencies(self, task: Dict) -> bool:
        """
        检查任务依赖是否满足
        
        Returns:
            bool: 依赖是否满足
        """
        dependencies = task.get('dependencies', [])
        
        if not dependencies:
            return True
        
        for dep_id in dependencies:
            dep_task = self.pm.get_task(dep_id)
            if not dep_task or dep_task.get('status') != 'done':
                return False
        
        return True

    def calculate_agent_load(self, agent_id: str) -> float:
        """
        计算 Agent 负载分数
        
        考虑因素:
        - 当前任务数
        - 任务总工时
        - 历史表现
        
        Returns:
            float: 负载分数 (0-100)
        """
        # 获取 Agent 当前任务
        tasks = self.pm.get_tasks_by_assignee(agent_id, status='in_progress')
        
        if not tasks:
            return 0.0
        
        # 基础负载 (任务数)
        task_count_score = min(50, len(tasks) * 15)
        
        # 工时负载
        total_hours = sum(t.get('estimated_hours', 0) for t in tasks)
        hours_score = min(30, total_hours * 2)
        
        # 时间负载 (任务已进行时间)
        time_score = 0
        for task in tasks:
            started_at = task.get('started_at')
            if started_at:
                try:
                    start = datetime.fromisoformat(started_at)
                    elapsed_hours = (datetime.now() - start).total_seconds() / 3600
                    time_score += min(5, elapsed_hours / 4)  # 每 4 小时增加 1 分
                except Exception:
                    pass
        
        total_score = task_count_score + hours_score + time_score
        self.agent_load[agent_id] = min(100, total_score)
        
        return self.agent_load[agent_id]

    def get_available_agents(self, required_skills: List[str] = None) -> List[str]:
        """
        获取可用的 Agent 列表
        
        Args:
            required_skills: 需要的技能列表
            
        Returns:
            List[str]: 可用 Agent ID 列表
        """
        # 预定义的 Agent 列表及其技能
        agents = {
            'architect': ['dev', 'architecture', 'design'],
            'developer': ['dev', 'python', 'javascript'],
            'tester': ['test', 'qa', 'automation'],
            'factor': ['data', 'analysis', 'factor'],
            'sentiment': ['data', 'nlp', 'analysis'],
            'fundamental': ['data', 'analysis', 'finance'],
            'trader': ['trade', 'execution', 'risk'],
            'risk': ['risk', 'analysis', 'monitoring'],
            'guard': ['review', 'audit', 'risk'],
            'backtest': ['backtest', 'analysis', 'data'],
            'strategist': ['strategy', 'communication', 'analysis'],
            'pm': ['management', 'coordination'],
            'ops': ['ops', 'monitoring', 'deployment']
        }
        
        available = []
        
        for agent_id, skills in agents.items():
            # 检查技能匹配
            if required_skills:
                if not any(skill in skills for skill in required_skills):
                    continue
            
            # 检查负载
            load = self.calculate_agent_load(agent_id)
            if load < 80:  # 负载低于 80 才可用
                available.append((agent_id, load))
        
        # 按负载排序
        available.sort(key=lambda x: x[1])
        
        return [agent_id for agent_id, _ in available]

    def assign_task(self, task_id: str, auto: bool = True, assignee: str = None) -> Optional[str]:
        """
        分配任务给 Agent
        
        Args:
            task_id: 任务 ID
            auto: 是否自动分配
            assignee: 指定负责人 (如果 auto=False)
            
        Returns:
            Optional[str]: 分配的 Agent ID
        """
        task = self.pm.get_task(task_id)
        if not task:
            logger.error(f"任务不存在：{task_id}")
            return None
        
        # 检查依赖
        if not self.check_dependencies(task):
            logger.warning(f"任务 {task_id} 依赖未满足")
            return None
        
        if auto:
            # 自动分配
            required_skills = task.get('metadata', {}).get('required_skills', [])
            available_agents = self.get_available_agents(required_skills)
            
            if not available_agents:
                logger.warning(f"没有可用的 Agent 分配给任务 {task_id}")
                return None
            
            # 选择负载最低的 Agent
            best_agent = available_agents[0]
            assignee = best_agent
        
        # 分配任务
        self.pm.assign_task(task_id, assignee)
        self.pm.update_task_status(task_id, 'in_progress')
        
        # 记录日志
        self.pm.log_work(
            task_id,
            f"任务分配给 {assignee}",
            log_type="assignment",
            agent_id=assignee
        )
        
        logger.info(f"任务 {task_id} 分配给 {assignee}")
        return assignee

    def schedule_tasks(self, project_id: str, limit: int = 10) -> List[Dict]:
        """
        调度项目下的待办任务
        
        Args:
            project_id: 项目 ID
            limit: 最多调度任务数
            
        Returns:
            List[Dict]: 已调度的任务列表
        """
        # 获取所有待办任务
        todo_tasks = self.pm.get_tasks_by_project(project_id, status='todo')
        
        if not todo_tasks:
            logger.info(f"项目 {project_id} 没有待办任务")
            return []
        
        # 计算优先级分数并排序
        scored_tasks = []
        for task in todo_tasks:
            score = self.calculate_priority_score(task)
            scored_tasks.append((task, score))
        
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        
        # 分配任务
        scheduled = []
        for task, score in scored_tasks[:limit]:
            assigned_agent = self.assign_task(task['task_id'], auto=True)
            
            if assigned_agent:
                scheduled.append({
                    'task_id': task['task_id'],
                    'task_name': task['name'],
                    'assigned_to': assigned_agent,
                    'priority_score': score
                })
        
        logger.info(f"调度了 {len(scheduled)} 个任务")
        return scheduled

    def get_task_queue(self, project_id: str) -> List[Dict]:
        """
        获取任务队列 (按优先级排序)
        
        Args:
            project_id: 项目 ID
            
        Returns:
            List[Dict]: 任务队列
        """
        todo_tasks = self.pm.get_tasks_by_project(project_id, status='todo')
        
        # 计算优先级分数
        queue = []
        for task in todo_tasks:
            score = self.calculate_priority_score(task)
            dependencies_met = self.check_dependencies(task)
            
            queue.append({
                'task_id': task['task_id'],
                'task_name': task['name'],
                'priority': task['priority'],
                'priority_score': score,
                'dependencies_met': dependencies_met,
                'assignee': task['assignee'],
                'due_date': task['due_date']
            })
        
        # 按优先级分数排序
        queue.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return queue

    def rebalance_tasks(self) -> Dict:
        """
        重新平衡任务负载
        
        Returns:
            Dict: 重新分配的结果
        """
        # 计算所有 Agent 负载
        agents = [
            'architect', 'developer', 'tester', 'factor', 'sentiment',
            'fundamental', 'trader', 'risk', 'guard', 'backtest',
            'strategist', 'pm', 'ops'
        ]
        
        loads = {}
        for agent in agents:
            loads[agent] = self.calculate_agent_load(agent)
        
        # 找出过载和空闲的 Agent
        overloaded = [a for a, l in loads.items() if l > 80]
        underloaded = [a for a, l in loads.items() if l < 30]
        
        result = {
            'overloaded': overloaded,
            'underloaded': underloaded,
            'loads': loads,
            'reassignments': []
        }
        
        # 重新分配逻辑 (简化版)
        for agent in overloaded:
            tasks = self.pm.get_tasks_by_assignee(agent, status='in_progress')
            if tasks and underloaded:
                # 将最新任务重新分配给空闲 Agent
                target = underloaded.pop(0)
                task = tasks[-1]
                self.pm.assign_task(task['task_id'], target)
                
                result['reassignments'].append({
                    'task_id': task['task_id'],
                    'from': agent,
                    'to': target
                })
        
        logger.info(f"任务重新平衡完成：{len(result['reassignments'])} 个任务被重新分配")
        return result

    def get_agent_utilization(self) -> Dict:
        """
        获取 Agent 利用率统计
        
        Returns:
            Dict: 利用率统计
        """
        agents = [
            'architect', 'developer', 'tester', 'factor', 'sentiment',
            'fundamental', 'trader', 'risk', 'guard', 'backtest',
            'strategist', 'pm', 'ops'
        ]
        
        utilization = {}
        
        for agent in agents:
            load = self.calculate_agent_load(agent)
            tasks = self.pm.get_tasks_by_assignee(agent)
            
            completed = len([t for t in tasks if t.get('status') == 'done'])
            in_progress = len([t for t in tasks if t.get('status') == 'in_progress'])
            
            utilization[agent] = {
                'load_score': load,
                'total_tasks': len(tasks),
                'completed': completed,
                'in_progress': in_progress,
                'utilization_rate': min(100, load)
            }
        
        return utilization


# ==================== 测试函数 ====================

def main():
    """测试函数"""
    pm = ProjectMaster()
    scheduler = TaskScheduler(pm)
    
    # 创建测试项目
    project_id = pm.create_project("测试项目", "Task Scheduler 测试")
    
    # 创建测试任务
    task1 = pm.create_task(
        project_id=project_id,
        name="任务 1 - 高优先级",
        priority="P0",
        estimated_hours=8,
        story_points=5
    )
    
    task2 = pm.create_task(
        project_id=project_id,
        name="任务 2 - 中优先级",
        priority="P2",
        estimated_hours=4,
        story_points=3
    )
    
    # 调度任务
    scheduled = scheduler.schedule_tasks(project_id)
    print("\n已调度任务:")
    for task in scheduled:
        print(f"  - {task['task_name']} -> {task['assigned_to']} (分数：{task['priority_score']})")
    
    # 获取利用率
    utilization = scheduler.get_agent_utilization()
    print("\nAgent 利用率:")
    for agent, stats in utilization.items():
        if stats['total_tasks'] > 0:
            print(f"  {agent}: 负载={stats['load_score']:.1f}, 任务={stats['total_tasks']}")


if __name__ == "__main__":
    from .project_master import ProjectMaster
    main()
