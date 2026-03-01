"""
Q 脑项目管理系统 - Project Master V2

核心模块:
- 项目管理主类
- 数据库持久化
- 与 OpenClaw 集成

作者：小七
版本：2.0
创建日期：2026-03-01
"""
import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pm.db')


# ==================== 枚举定义 ====================

class Priority(Enum):
    """任务优先级"""
    P0 = "P0"  # 关键路径 - 立即处理
    P1 = "P1"  # 重要任务 - 24 小时内
    P2 = "P2"  # 优化任务 - 本周内
    P3 = "P3"  # 可选任务 - 视情况而定


class TaskStatus(Enum):
    """任务状态"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class MilestoneStatus(Enum):
    """里程碑状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


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


# ==================== 数据库初始化 ====================

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 项目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            start_date DATE,
            end_date DATE,
            owner TEXT,
            metadata TEXT
        )
    ''')
    
    # 任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'P2',
            task_type TEXT DEFAULT 'dev',
            status TEXT DEFAULT 'todo',
            assignee TEXT,
            estimated_hours REAL DEFAULT 0,
            actual_hours REAL DEFAULT 0,
            story_points INTEGER DEFAULT 0,
            acceptance_criteria TEXT,
            dependencies TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            due_date DATE,
            metadata TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
    ''')
    
    # 里程碑表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            milestone_id TEXT UNIQUE NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'not_started',
            planned_start DATE,
            planned_end DATE,
            actual_start DATE,
            actual_end DATE,
            completion_criteria TEXT,
            progress REAL DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
    ''')
    
    # 工作日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id TEXT UNIQUE NOT NULL,
            task_id TEXT NOT NULL,
            agent_id TEXT,
            log_type TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    ''')
    
    # 验收记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id TEXT UNIQUE NOT NULL,
            task_id TEXT NOT NULL,
            reviewer TEXT,
            status TEXT DEFAULT 'pending',
            comments TEXT,
            quality_score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    ''')
    
    # 里程碑 - 任务关联表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS milestone_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            milestone_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            UNIQUE(milestone_id, task_id),
            FOREIGN KEY (milestone_id) REFERENCES milestones(milestone_id),
            FOREIGN KEY (task_id) REFERENCES tasks(task_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ 项目管理系统数据库初始化完成")


# ==================== 项目管理主类 ====================

class ProjectMaster:
    """
    Q 脑项目管理主类
    
    功能:
    - 项目管理
    - 任务管理
    - 里程碑管理
    - 工作日志
    - 验收系统
    """

    def __init__(self):
        init_db()
        logger.info("ProjectMaster 初始化完成")

    # ==================== 项目管理 ====================

    def create_project(
        self,
        name: str,
        description: str = "",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        owner: str = "PM",
        metadata: Dict = None
    ) -> str:
        """创建项目"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        project_id = f"PRJ-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        cursor.execute('''
            INSERT INTO projects (project_id, name, description, start_date, end_date, owner, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id, name, description,
            start_date.isoformat() if start_date else None,
            end_date.isoformat() if end_date else None,
            owner,
            json.dumps(metadata) if metadata else None,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"创建项目：{project_id} - {name}")
        return project_id

    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取项目信息"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM projects WHERE project_id = ?', (project_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_project(row)
        return None

    def get_all_projects(self, status: str = None) -> List[Dict]:
        """获取所有项目"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM projects WHERE status = ? ORDER BY created_at DESC', (status,))
        else:
            cursor.execute('SELECT * FROM projects ORDER BY created_at DESC')
        
        projects = [self._row_to_project(row) for row in cursor.fetchall()]
        conn.close()
        
        return projects

    def update_project_status(self, project_id: str, status: str):
        """更新项目状态"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE projects SET status = ?, updated_at = ?
            WHERE project_id = ?
        ''', (status, datetime.now(), project_id))
        
        conn.commit()
        conn.close()
        logger.info(f"项目 {project_id} 状态更新为：{status}")

    def _row_to_project(self, row) -> Dict:
        """将数据库行转换为项目字典"""
        return {
            'id': row[0],
            'project_id': row[1],
            'name': row[2],
            'description': row[3],
            'status': row[4],
            'created_at': row[5],
            'updated_at': row[6],
            'start_date': row[7],
            'end_date': row[8],
            'owner': row[9],
            'metadata': json.loads(row[10]) if row[10] else {}
        }

    # ==================== 任务管理 ====================

    def create_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        priority: str = "P2",
        task_type: str = "dev",
        estimated_hours: float = 0,
        story_points: int = 0,
        assignee: str = None,
        acceptance_criteria: List[str] = None,
        dependencies: List[str] = None,
        due_date: Optional[date] = None,
        metadata: Dict = None
    ) -> str:
        """创建任务"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        task_id = f"TASK-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        cursor.execute('''
            INSERT INTO tasks (
                task_id, project_id, name, description, priority, task_type,
                estimated_hours, story_points, assignee, acceptance_criteria,
                dependencies, due_date, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id, project_id, name, description, priority, task_type,
            estimated_hours, story_points, assignee,
            json.dumps(acceptance_criteria) if acceptance_criteria else None,
            json.dumps(dependencies) if dependencies else None,
            due_date.isoformat() if due_date else None,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"创建任务：{task_id} - {name}")
        return task_id

    def update_task_status(self, task_id: str, status: str):
        """更新任务状态"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        if status == 'in_progress':
            cursor.execute('''
                UPDATE tasks SET status = ?, started_at = ?
                WHERE task_id = ?
            ''', (status, now, task_id))
        elif status == 'done':
            cursor.execute('''
                UPDATE tasks SET status = ?, completed_at = ?
                WHERE task_id = ?
            ''', (status, now, task_id))
        else:
            cursor.execute('UPDATE tasks SET status = ? WHERE task_id = ?', (status, task_id))
        
        conn.commit()
        conn.close()
        logger.info(f"任务 {task_id} 状态更新为：{status}")

    def assign_task(self, task_id: str, assignee: str):
        """分配任务"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE tasks SET assignee = ? WHERE task_id = ?', (assignee, task_id))
        
        conn.commit()
        conn.close()
        logger.info(f"任务 {task_id} 分配给：{assignee}")

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务信息"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_task(row)
        return None

    def get_tasks_by_project(self, project_id: str, status: str = None) -> List[Dict]:
        """获取项目下的所有任务"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM tasks WHERE project_id = ? AND status = ?', (project_id, status))
        else:
            cursor.execute('SELECT * FROM tasks WHERE project_id = ?', (project_id,))
        
        tasks = [self._row_to_task(row) for row in cursor.fetchall()]
        conn.close()
        
        return tasks

    def get_tasks_by_assignee(self, assignee: str, status: str = None) -> List[Dict]:
        """获取负责人的任务"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM tasks WHERE assignee = ? AND status = ?', (assignee, status))
        else:
            cursor.execute('SELECT * FROM tasks WHERE assignee = ?', (assignee,))
        
        tasks = [self._row_to_task(row) for row in cursor.fetchall()]
        conn.close()
        
        return tasks

    def _row_to_task(self, row) -> Dict:
        """将数据库行转换为任务字典"""
        return {
            'id': row[0],
            'task_id': row[1],
            'project_id': row[2],
            'name': row[3],
            'description': row[4],
            'priority': row[5],
            'task_type': row[6],
            'status': row[7],
            'assignee': row[8],
            'estimated_hours': row[9],
            'actual_hours': row[10],
            'story_points': row[11],
            'acceptance_criteria': json.loads(row[12]) if row[12] else [],
            'dependencies': json.loads(row[13]) if row[13] else [],
            'created_at': row[14],
            'started_at': row[15],
            'completed_at': row[16],
            'due_date': row[17],
            'metadata': json.loads(row[18]) if row[18] else {}
        }

    # ==================== 里程碑管理 ====================

    def create_milestone(
        self,
        project_id: str,
        name: str,
        description: str = "",
        planned_start: Optional[date] = None,
        planned_end: Optional[date] = None,
        completion_criteria: List[str] = None
    ) -> str:
        """创建里程碑"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        milestone_id = f"M-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        cursor.execute('''
            INSERT INTO milestones (
                milestone_id, project_id, name, description,
                planned_start, planned_end, completion_criteria
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            milestone_id, project_id, name, description,
            planned_start.isoformat() if planned_start else None,
            planned_end.isoformat() if planned_end else None,
            json.dumps(completion_criteria) if completion_criteria else None
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"创建里程碑：{milestone_id} - {name}")
        return milestone_id

    def add_task_to_milestone(self, milestone_id: str, task_id: str):
        """添加任务到里程碑"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO milestone_tasks (milestone_id, task_id)
            VALUES (?, ?)
        ''', (milestone_id, task_id))
        
        # 更新里程碑进度
        self._update_milestone_progress(milestone_id)
        
        conn.commit()
        conn.close()
        logger.info(f"任务 {task_id} 添加到里程碑 {milestone_id}")

    def _update_milestone_progress(self, milestone_id: str):
        """更新里程碑进度"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取里程碑下的所有任务
        cursor.execute('SELECT task_id FROM milestone_tasks WHERE milestone_id = ?', (milestone_id,))
        task_ids = [row[0] for row in cursor.fetchall()]
        
        if task_ids:
            # 计算完成的任务数
            placeholders = ','.join('?' * len(task_ids))
            cursor.execute(f'''
                SELECT COUNT(*) FROM tasks 
                WHERE task_id IN ({placeholders}) AND status = 'done'
            ''', task_ids)
            completed = cursor.fetchone()[0]
            
            progress = (completed / len(task_ids)) * 100
            
            # 更新里程碑状态
            if progress == 100:
                status = 'completed'
                actual_end = date.today().isoformat()
                cursor.execute('''
                    UPDATE milestones SET progress = ?, status = ?, actual_end = ?
                    WHERE milestone_id = ?
                ''', (progress, status, actual_end, milestone_id))
            elif progress > 0:
                status = 'in_progress'
                cursor.execute('''
                    UPDATE milestones SET progress = ?, status = ?
                    WHERE milestone_id = ?
                ''', (progress, status, milestone_id))
        
        conn.commit()
        conn.close()

    def get_milestone(self, milestone_id: str) -> Optional[Dict]:
        """获取里程碑信息"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM milestones WHERE milestone_id = ?', (milestone_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_milestone(row)
        return None

    def get_milestones_by_project(self, project_id: str) -> List[Dict]:
        """获取项目下的所有里程碑"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM milestones WHERE project_id = ? ORDER BY planned_start', (project_id,))
        milestones = [self._row_to_milestone(row) for row in cursor.fetchall()]
        conn.close()
        
        return milestones

    def _row_to_milestone(self, row) -> Dict:
        """将数据库行转换为里程碑字典"""
        return {
            'id': row[0],
            'milestone_id': row[1],
            'project_id': row[2],
            'name': row[3],
            'description': row[4],
            'status': row[5],
            'planned_start': row[6],
            'planned_end': row[7],
            'actual_start': row[8],
            'actual_end': row[9],
            'completion_criteria': json.loads(row[10]) if row[10] else [],
            'progress': row[11]
        }

    # ==================== 工作日志 ====================

    def log_work(
        self,
        task_id: str,
        message: str,
        log_type: str = "progress",
        agent_id: str = None,
        details: Dict = None
    ) -> str:
        """记录工作日志"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        log_id = f"LOG-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        
        cursor.execute('''
            INSERT INTO work_logs (log_id, task_id, agent_id, log_type, message, details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            log_id, task_id, agent_id, log_type, message,
            json.dumps(details) if details else None
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"记录工作日志：{log_id}")
        return log_id

    def get_work_logs(self, task_id: str) -> List[Dict]:
        """获取任务的工作日志"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM work_logs WHERE task_id = ? ORDER BY created_at DESC', (task_id,))
        logs = [self._row_to_log(row) for row in cursor.fetchall()]
        conn.close()
        
        return logs

    def _row_to_log(self, row) -> Dict:
        """将数据库行转换为日志字典"""
        return {
            'id': row[0],
            'log_id': row[1],
            'task_id': row[2],
            'agent_id': row[3],
            'log_type': row[4],
            'message': row[5],
            'details': json.loads(row[6]) if row[6] else {},
            'created_at': row[7]
        }

    # ==================== 验收系统 ====================

    def create_review(
        self,
        task_id: str,
        reviewer: str = "PM"
    ) -> str:
        """创建验收记录"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        review_id = f"REV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        cursor.execute('''
            INSERT INTO reviews (review_id, task_id, reviewer)
            VALUES (?, ?, ?)
        ''', (review_id, task_id, reviewer))
        
        conn.commit()
        conn.close()
        
        logger.info(f"创建验收记录：{review_id}")
        return review_id

    def complete_review(
        self,
        review_id: str,
        status: str,
        comments: str = "",
        quality_score: int = None
    ):
        """完成验收"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE reviews SET status = ?, comments = ?, quality_score = ?, reviewed_at = ?
            WHERE review_id = ?
        ''', (status, comments, quality_score, datetime.now(), review_id))
        
        conn.commit()
        conn.close()
        logger.info(f"验收记录 {review_id} 完成：{status}")

    def get_reviews_by_task(self, task_id: str) -> List[Dict]:
        """获取任务的验收记录"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM reviews WHERE task_id = ? ORDER BY created_at DESC', (task_id,))
        reviews = [self._row_to_review(row) for row in cursor.fetchall()]
        conn.close()
        
        return reviews

    def _row_to_review(self, row) -> Dict:
        """将数据库行转换为验收记录字典"""
        return {
            'id': row[0],
            'review_id': row[1],
            'task_id': row[2],
            'reviewer': row[3],
            'status': row[4],
            'comments': row[5],
            'quality_score': row[6],
            'created_at': row[7],
            'reviewed_at': row[8]
        }

    # ==================== 统计报表 ====================

    def get_project_stats(self, project_id: str) -> Dict:
        """获取项目统计"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 任务统计
        cursor.execute('''
            SELECT status, COUNT(*) FROM tasks WHERE project_id = ? GROUP BY status
        ''', (project_id,))
        task_status = dict(cursor.fetchall())
        
        # 里程碑统计
        cursor.execute('''
            SELECT status, COUNT(*) FROM milestones WHERE project_id = ? GROUP BY status
        ''', (project_id,))
        milestone_status = dict(cursor.fetchall())
        
        # 总工时
        cursor.execute('''
            SELECT SUM(actual_hours), SUM(estimated_hours) FROM tasks WHERE project_id = ?
        ''', (project_id,))
        hours_row = cursor.fetchone()
        
        # 故事点
        cursor.execute('''
            SELECT SUM(story_points) FROM tasks WHERE project_id = ?
        ''', (project_id,))
        sp_row = cursor.fetchone()
        
        conn.close()
        
        return {
            'project_id': project_id,
            'task_status': task_status,
            'milestone_status': milestone_status,
            'total_hours': hours_row[0] or 0,
            'estimated_hours': hours_row[1] or 0,
            'total_story_points': sp_row[0] or 0,
            'completed_story_points': self._get_completed_story_points(project_id)
        }

    def _get_completed_story_points(self, project_id: str) -> int:
        """获取已完成的故事点"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(story_points) FROM tasks 
            WHERE project_id = ? AND status = 'done'
        ''', (project_id,))
        row = cursor.fetchone()
        conn.close()
        
        return row[0] or 0

    def get_dashboard_data(self) -> Dict:
        """获取 Dashboard 数据"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 项目统计
        cursor.execute('SELECT status, COUNT(*) FROM projects GROUP BY status')
        project_stats = dict(cursor.fetchall())
        
        # 任务统计
        cursor.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status')
        task_stats = dict(cursor.fetchall())
        
        # 今日完成
        today = date.today().isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM tasks 
            WHERE status = 'done' AND date(completed_at) = ?
        ''', (today,))
        today_completed = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'project_stats': project_stats,
            'task_stats': task_stats,
            'today_completed': today_completed,
            'total_projects': sum(project_stats.values()),
            'total_tasks': sum(task_stats.values())
        }


# ==================== 测试函数 ====================

def main():
    """测试函数"""
    pm = ProjectMaster()
    
    # 创建项目
    project_id = pm.create_project(
        name="Q 脑系统 V2",
        description="量化交易系统升级",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
        owner="PM"
    )
    
    # 创建里程碑
    m1 = pm.create_milestone(
        project_id=project_id,
        name="M1: 基础架构",
        description="完成系统核心框架",
        planned_start=date.today(),
        planned_end=date.today() + timedelta(days=30),
        completion_criteria=["代码仓库完整", "数据库可用", "日志可追踪"]
    )
    
    # 创建任务
    task1 = pm.create_task(
        project_id=project_id,
        name="项目初始化",
        description="创建 Git 仓库和基本结构",
        priority="P0",
        task_type="dev",
        estimated_hours=4,
        story_points=3,
        acceptance_criteria=["仓库创建", "目录结构完整", "README 编写"]
    )
    
    # 关联里程碑
    pm.add_task_to_milestone(m1, task1)
    
    # 分配任务
    pm.assign_task(task1, "architect")
    
    # 更新状态
    pm.update_task_status(task1, "in_progress")
    
    # 记录日志
    pm.log_work(task1, "开始项目初始化", agent_id="architect")
    
    # 获取统计
    stats = pm.get_project_stats(project_id)
    print("\n项目统计:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    dashboard = pm.get_dashboard_data()
    print("\nDashboard 数据:")
    print(json.dumps(dashboard, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
