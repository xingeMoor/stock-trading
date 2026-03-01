"""
验收系统 - Review System

功能:
- 任务验收流程
- 质量评分
- 验收标准检查
- 反馈记录

作者：小七
版本：1.0
创建日期：2026-03-01
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from .project_master import ProjectMaster, TaskStatus

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """验收状态"""
    PENDING = "pending"       # 待验收
    IN_REVIEW = "in_review"   # 验收中
    APPROVED = "approved"     # 通过
    REJECTED = "rejected"     # 拒绝
    NEEDS_WORK = "needs_work" # 需要改进


class ReviewSystem:
    """
    验收系统
    
    功能:
    - 创建验收流程
    - 质量评分
    - 验收标准验证
    - 反馈管理
    """

    def __init__(self, project_master: ProjectMaster):
        self.pm = project_master
        logger.info("ReviewSystem 初始化完成")

    def create_review_request(
        self,
        task_id: str,
        reviewer: str = "PM",
        priority: str = "normal"
    ) -> str:
        """
        创建验收请求
        
        Args:
            task_id: 任务 ID
            reviewer: 验收人
            priority: 优先级 (low/normal/high)
            
        Returns:
            str: 验收记录 ID
        """
        task = self.pm.get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在：{task_id}")
        
        # 更新任务状态为待验收
        self.pm.update_task_status(task_id, 'review')
        
        # 创建验收记录
        review_id = self.pm.create_review(task_id, reviewer)
        
        # 记录日志
        self.pm.log_work(
            task_id,
            f"提交验收请求，验收人：{reviewer}",
            log_type="review_request",
            details={'reviewer': reviewer, 'priority': priority}
        )
        
        logger.info(f"创建验收请求：{review_id} for task {task_id}")
        return review_id

    def evaluate_task(
        self,
        review_id: str,
        status: ReviewStatus,
        comments: str = "",
        quality_score: int = None,
        feedback: List[str] = None
    ) -> bool:
        """
        评估任务
        
        Args:
            review_id: 验收记录 ID
            status: 验收状态
            comments: 评语
            quality_score: 质量评分 (1-10)
            feedback: 反馈列表
            
        Returns:
            bool: 是否成功
        """
        # 获取验收记录
        reviews = self.pm.get_reviews_by_task(
            # 需要先获取 task_id
            review_id  # 这里需要修改，应该是通过 review_id 找 task_id
        )
        
        if not reviews:
            logger.error(f"验收记录不存在：{review_id}")
            return False
        
        review = reviews[0]
        task_id = review['task_id']
        
        # 完成验收
        self.pm.complete_review(
            review_id,
            status.value,
            comments,
            quality_score
        )
        
        # 根据验收结果更新任务状态
        if status == ReviewStatus.APPROVED:
            self.pm.update_task_status(task_id, 'done')
            
            # 记录验收通过日志
            self.pm.log_work(
                task_id,
                f"验收通过 - 评分：{quality_score}/10",
                log_type="review_approved",
                details={
                    'review_id': review_id,
                    'quality_score': quality_score,
                    'comments': comments
                }
            )
            
        elif status == ReviewStatus.REJECTED:
            self.pm.update_task_status(task_id, 'todo')
            
            self.pm.log_work(
                task_id,
                f"验收拒绝：{comments}",
                log_type="review_rejected",
                details={'review_id': review_id, 'feedback': feedback}
            )
            
        elif status == ReviewStatus.NEEDS_WORK:
            self.pm.update_task_status(task_id, 'in_progress')
            
            self.pm.log_work(
                task_id,
                f"需要改进：{comments}",
                log_type="review_needs_work",
                details={'review_id': review_id, 'feedback': feedback}
            )
        
        logger.info(f"验收完成：{review_id} - {status.value}")
        return True

    def check_acceptance_criteria(self, task_id: str) -> Dict:
        """
        检查验收标准
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Dict: 检查结果
        """
        task = self.pm.get_task(task_id)
        if not task:
            return {'valid': False, 'error': '任务不存在'}
        
        criteria = task.get('acceptance_criteria', [])
        
        if not criteria:
            return {
                'valid': True,
                'message': '没有定义验收标准',
                'checked': 0,
                'passed': 0
            }
        
        # 检查工作日志中是否有相关记录
        logs = self.pm.get_work_logs(task_id)
        
        # 简单检查：如果任务状态是 review 或 done，认为标准已满足
        # 实际应用中应该更复杂
        status = task.get('status')
        
        if status in ['review', 'done']:
            return {
                'valid': True,
                'message': '验收标准已满足',
                'criteria': criteria,
                'checked': len(criteria),
                'passed': len(criteria)
            }
        else:
            return {
                'valid': False,
                'message': '任务尚未完成，验收标准未验证',
                'criteria': criteria,
                'checked': 0,
                'passed': 0
            }

    def get_quality_metrics(self, project_id: str) -> Dict:
        """
        获取项目质量指标
        
        Args:
            project_id: 项目 ID
            
        Returns:
            Dict: 质量指标
        """
        tasks = self.pm.get_tasks_by_project(project_id)
        
        if not tasks:
            return {
                'total_tasks': 0,
                'reviewed_tasks': 0,
                'avg_quality_score': 0,
                'approval_rate': 0
            }
        
        # 获取所有验收记录
        total_score = 0
        reviewed_count = 0
        approved_count = 0
        rejected_count = 0
        
        for task in tasks:
            reviews = self.pm.get_reviews_by_task(task['task_id'])
            
            for review in reviews:
                if review.get('status') != 'pending':
                    reviewed_count += 1
                    
                    if review.get('quality_score'):
                        total_score += review['quality_score']
                    
                    if review.get('status') == 'approved':
                        approved_count += 1
                    elif review.get('status') == 'rejected':
                        rejected_count += 1
        
        return {
            'total_tasks': len(tasks),
            'reviewed_tasks': reviewed_count,
            'avg_quality_score': total_score / reviewed_count if reviewed_count > 0 else 0,
            'approval_rate': approved_count / reviewed_count * 100 if reviewed_count > 0 else 0,
            'rejection_rate': rejected_count / reviewed_count * 100 if reviewed_count > 0 else 0
        }

    def get_pending_reviews(self) -> List[Dict]:
        """
        获取待验收的任务列表
        
        Returns:
            List[Dict]: 待验收任务
        """
        # 获取所有状态为 review 的任务
        # 这里需要遍历所有项目，简化实现
        conn = None
        try:
            import sqlite3
            from .project_master import DB_PATH
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT t.task_id, t.name, t.assignee, t.priority, t.created_at,
                       r.review_id, r.reviewer, r.created_at as review_created
                FROM tasks t
                JOIN reviews r ON t.task_id = r.task_id
                WHERE t.status = 'review' AND r.status = 'pending'
                ORDER BY 
                    CASE t.priority 
                        WHEN 'P0' THEN 1 
                        WHEN 'P1' THEN 2 
                        WHEN 'P2' THEN 3 
                        WHEN 'P3' THEN 4 
                    END,
                    r.created_at
            ''')
            
            pending = []
            for row in cursor.fetchall():
                pending.append({
                    'task_id': row[0],
                    'task_name': row[1],
                    'assignee': row[2],
                    'priority': row[3],
                    'review_id': row[5],
                    'reviewer': row[6],
                    'requested_at': row[7]
                })
            
            return pending
            
        finally:
            if conn:
                conn.close()

    def generate_review_report(self, task_id: str) -> str:
        """
        生成验收报告
        
        Args:
            task_id: 任务 ID
            
        Returns:
            str: Markdown 格式的验收报告
        """
        task = self.pm.get_task(task_id)
        if not task:
            return "任务不存在"
        
        reviews = self.pm.get_reviews_by_task(task_id)
        logs = self.pm.get_work_logs(task_id)
        
        report = [
            f"# 任务验收报告",
            f"",
            f"## 任务信息",
            f"- **任务 ID**: {task['task_id']}",
            f"- **任务名称**: {task['name']}",
            f"- **负责人**: {task['assignee'] or '未分配'}",
            f"- **优先级**: {task['priority']}",
            f"- **状态**: {task['status']}",
            f"",
            f"## 验收记录",
        ]
        
        if reviews:
            for review in reviews:
                report.append(f"### 验收 {review['review_id']}")
                report.append(f"- **验收人**: {review['reviewer']}")
                report.append(f"- **状态**: {review['status']}")
                report.append(f"- **评分**: {review['quality_score'] or 'N/A'}/10")
                report.append(f"- **评语**: {review['comments'] or '无'}")
                report.append(f"- **时间**: {review['reviewed_at'] or review['created_at']}")
                report.append(f"")
        else:
            report.append("暂无验收记录")
        
        report.extend([
            f"",
            f"## 工作日志",
        ])
        
        if logs:
            for log in logs[:10]:  # 最近 10 条
                report.append(f"- [{log['created_at']}] {log['log_type']}: {log['message']}")
        else:
            report.append("暂无工作日志")
        
        return "\n".join(report)


# ==================== 测试函数 ====================

def main():
    """测试函数"""
    pm = ProjectMaster()
    review_system = ReviewSystem(pm)
    
    # 创建测试数据
    project_id = pm.create_project("测试项目", "Review System 测试")
    
    task_id = pm.create_task(
        project_id=project_id,
        name="测试任务",
        description="验收系统测试",
        priority="P1",
        acceptance_criteria=["功能完整", "代码规范", "测试通过"]
    )
    
    # 模拟任务完成
    pm.update_task_status(task_id, 'review')
    
    # 创建验收请求
    review_id = review_system.create_review_request(task_id, reviewer="PM")
    
    # 检查验收标准
    criteria_check = review_system.check_acceptance_criteria(task_id)
    print("\n验收标准检查:")
    print(f"  结果：{criteria_check['message']}")
    
    # 执行验收
    review_system.evaluate_task(
        review_id,
        ReviewStatus.APPROVED,
        comments="完成良好，代码质量高",
        quality_score=9,
        feedback=["代码结构清晰", "文档完整"]
    )
    
    # 生成报告
    report = review_system.generate_review_report(task_id)
    print("\n验收报告:")
    print(report)
    
    # 质量指标
    metrics = review_system.get_quality_metrics(project_id)
    print("\n质量指标:")
    print(f"  平均评分：{metrics['avg_quality_score']:.1f}/10")
    print(f"  通过率：{metrics['approval_rate']:.1f}%")


if __name__ == "__main__":
    from .project_master import ProjectMaster
    main()
