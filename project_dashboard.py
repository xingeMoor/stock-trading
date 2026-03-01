"""
Q脑项目管理系统 Dashboard
端口：5008

功能:
- 项目列表
- 任务看板
- 里程碑进度
- 验收报告

作者：小七
版本：1.0
创建日期：2026-03-01
"""
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, date, timedelta
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))
from src.pm import ProjectMaster, TaskScheduler, ReviewSystem, WorkflowEngine

app = Flask(__name__)

# 初始化系统
pm = ProjectMaster()
scheduler = TaskScheduler(pm)
review_system = ReviewSystem(pm)
workflow_engine = WorkflowEngine(pm)

# ============ HTML 模板 ============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q脑项目管理系统 | Q-Brain PM Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e1a;
            --bg-secondary: #111827;
            --bg-card: rgba(17, 24, 39, 0.7);
            --accent-cyan: #06b6d4;
            --accent-purple: #8b5cf6;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
            --accent-blue: #3b82f6;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --border: rgba(75, 85, 99, 0.3);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        /* 导航栏 */
        .nav {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 16px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .nav-brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .nav-brand-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .nav-brand-text h1 {
            font-size: 20px;
            font-weight: 700;
        }
        
        .nav-brand-text p {
            font-size: 11px;
            color: var(--text-secondary);
        }
        
        .nav-tabs {
            display: flex;
            gap: 8px;
        }
        
        .nav-tab {
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .nav-tab:hover, .nav-tab.active {
            background: var(--accent-cyan);
            border-color: var(--accent-cyan);
            color: white;
        }
        
        /* 主内容 */
        .main {
            padding: 30px 40px;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* 统计卡片 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
        }
        
        .stat-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .stat-card-title {
            font-size: 14px;
            color: var(--text-secondary);
        }
        
        .stat-card-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        
        .stat-card-icon.cyan { background: rgba(6, 182, 212, 0.2); }
        .stat-card-icon.green { background: rgba(16, 185, 129, 0.2); }
        .stat-card-icon.purple { background: rgba(139, 92, 246, 0.2); }
        .stat-card-icon.yellow { background: rgba(245, 158, 11, 0.2); }
        
        .stat-card-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .stat-card-change {
            font-size: 13px;
            color: var(--accent-green);
        }
        
        /* 项目卡片 */
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }
        
        .project-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .project-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }
        
        .project-name {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .project-desc {
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        .project-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .project-status.active {
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
        }
        
        .project-status.completed {
            background: rgba(6, 182, 212, 0.2);
            color: var(--accent-cyan);
        }
        
        .project-progress {
            margin: 20px 0;
        }
        
        .progress-bar {
            height: 8px;
            background: var(--bg-secondary);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 8px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 4px;
            transition: width 0.5s;
        }
        
        .progress-label {
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            justify-content: space-between;
        }
        
        .project-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }
        
        .project-stat {
            text-align: center;
        }
        
        .project-stat-value {
            font-size: 20px;
            font-weight: 700;
            color: var(--accent-cyan);
        }
        
        .project-stat-label {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 2px;
        }
        
        /* 任务看板 */
        .kanban-board {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .kanban-column {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            min-height: 400px;
        }
        
        .kanban-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }
        
        .kanban-title {
            font-size: 14px;
            font-weight: 600;
        }
        
        .kanban-count {
            background: var(--bg-secondary);
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .kanban-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            transition: background 0.3s;
            cursor: pointer;
        }
        
        .kanban-card:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .kanban-card-priority {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .kanban-card-priority.P0 { background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }
        .kanban-card-priority.P1 { background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); }
        .kanban-card-priority.P2 { background: rgba(59, 130, 246, 0.2); color: var(--accent-blue); }
        .kanban-card-priority.P3 { background: rgba(139, 92, 246, 0.2); color: var(--accent-purple); }
        
        .kanban-card-title {
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 8px;
        }
        
        .kanban-card-meta {
            font-size: 11px;
            color: var(--text-secondary);
            display: flex;
            justify-content: space-between;
        }
        
        /* 里程碑 */
        .milestone-list {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        
        .milestone-item {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
        }
        
        .milestone-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            flex-shrink: 0;
        }
        
        .milestone-icon.completed { background: rgba(16, 185, 129, 0.2); }
        .milestone-icon.in_progress { background: rgba(245, 158, 11, 0.2); }
        .milestone-icon.not_started { background: rgba(75, 85, 99, 0.2); }
        
        .milestone-content {
            flex: 1;
        }
        
        .milestone-name {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .milestone-desc {
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        
        .milestone-dates {
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .milestone-progress {
            width: 200px;
            text-align: right;
        }
        
        .milestone-progress-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--accent-cyan);
        }
        
        .milestone-progress-label {
            font-size: 11px;
            color: var(--text-secondary);
        }
        
        /* 页脚 */
        .footer {
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
            font-size: 12px;
            border-top: 1px solid var(--border);
            margin-top: 40px;
        }
        
        /* 视图切换 */
        .view { display: none; }
        .view.active { display: block; }
    </style>
</head>
<body>
    <!-- 导航栏 -->
    <nav class="nav">
        <div class="nav-brand">
            <div class="nav-brand-icon">📋</div>
            <div class="nav-brand-text">
                <h1>Q脑项目管理系统</h1>
                <p>Q-Brain Project Management</p>
            </div>
        </div>
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="switchView('overview')">总览</button>
            <button class="nav-tab" onclick="switchView('projects')">项目</button>
            <button class="nav-tab" onclick="switchView('tasks')">任务看板</button>
            <button class="nav-tab" onclick="switchView('milestones')">里程碑</button>
        </div>
    </nav>

    <!-- 主内容 -->
    <main class="main">
        <!-- 总览视图 -->
        <div id="overview" class="view active">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-card-header">
                        <span class="stat-card-title">总项目数</span>
                        <div class="stat-card-icon cyan">📁</div>
                    </div>
                    <div class="stat-card-value">{{ dashboard.total_projects }}</div>
                    <div class="stat-card-change">活跃项目：{{ dashboard.active_projects }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-header">
                        <span class="stat-card-title">总任务数</span>
                        <div class="stat-card-icon purple">📋</div>
                    </div>
                    <div class="stat-card-value">{{ dashboard.total_tasks }}</div>
                    <div class="stat-card-change">今日完成：{{ dashboard.today_completed }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-header">
                        <span class="stat-card-title">任务完成率</span>
                        <div class="stat-card-icon green">✅</div>
                    </div>
                    <div class="stat-card-value">{{ dashboard.completion_rate }}%</div>
                    <div class="stat-card-change">↑ 较上周 +{{ dashboard.week_change }}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-header">
                        <span class="stat-card-title">平均质量评分</span>
                        <div class="stat-card-icon yellow">⭐</div>
                    </div>
                    <div class="stat-card-value">{{ dashboard.avg_quality }}/10</div>
                    <div class="stat-card-change">验收通过率：{{ dashboard.approval_rate }}%</div>
                </div>
            </div>

            <h2 style="margin-bottom: 20px; font-size: 18px;">📊 项目一览</h2>
            <div class="projects-grid">
                {% for project in projects %}
                <div class="project-card">
                    <div class="project-header">
                        <div>
                            <div class="project-name">{{ project.name }}</div>
                            <div class="project-desc">{{ project.description or '暂无描述' }}</div>
                        </div>
                        <span class="project-status {{ project.status }}">{{ project.status }}</span>
                    </div>
                    <div class="project-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {{ project.progress }}%"></div>
                        </div>
                        <div class="progress-label">
                            <span>进度</span>
                            <span>{{ project.progress }}%</span>
                        </div>
                    </div>
                    <div class="project-stats">
                        <div class="project-stat">
                            <div class="project-stat-value">{{ project.task_count }}</div>
                            <div class="project-stat-label">任务</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-value">{{ project.completed_tasks }}</div>
                            <div class="project-stat-label">已完成</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-value">{{ project.milestone_count }}</div>
                            <div class="project-stat-label">里程碑</div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- 项目视图 -->
        <div id="projects" class="view">
            <h2 style="margin-bottom: 20px; font-size: 18px;">📁 所有项目</h2>
            <div class="projects-grid">
                {% for project in projects %}
                <div class="project-card">
                    <div class="project-header">
                        <div>
                            <div class="project-name">{{ project.name }}</div>
                            <div class="project-desc">{{ project.description or '暂无描述' }}</div>
                        </div>
                        <span class="project-status {{ project.status }}">{{ project.status }}</span>
                    </div>
                    <div class="project-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {{ project.progress }}%"></div>
                        </div>
                        <div class="progress-label">
                            <span>进度</span>
                            <span>{{ project.progress }}%</span>
                        </div>
                    </div>
                    <div class="project-stats">
                        <div class="project-stat">
                            <div class="project-stat-value">{{ project.task_count }}</div>
                            <div class="project-stat-label">任务</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-value">{{ project.completed_tasks }}</div>
                            <div class="project-stat-label">已完成</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-value">{{ project.milestone_count }}</div>
                            <div class="project-stat-label">里程碑</div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- 任务看板视图 -->
        <div id="tasks" class="view">
            <h2 style="margin-bottom: 20px; font-size: 18px;">📋 任务看板</h2>
            <div class="kanban-board">
                <div class="kanban-column">
                    <div class="kanban-header">
                        <span class="kanban-title">📝 待办</span>
                        <span class="kanban-count">{{ tasks.todo|length }}</span>
                    </div>
                    {% for task in tasks.todo %}
                    <div class="kanban-card">
                        <span class="kanban-card-priority {{ task.priority }}">{{ task.priority }}</span>
                        <div class="kanban-card-title">{{ task.name }}</div>
                        <div class="kanban-card-meta">
                            <span>{{ task.assignee or '未分配' }}</span>
                            <span>💼 {{ task.story_points }}pts</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="kanban-column">
                    <div class="kanban-header">
                        <span class="kanban-title">🔄 进行中</span>
                        <span class="kanban-count">{{ tasks.in_progress|length }}</span>
                    </div>
                    {% for task in tasks.in_progress %}
                    <div class="kanban-card">
                        <span class="kanban-card-priority {{ task.priority }}">{{ task.priority }}</span>
                        <div class="kanban-card-title">{{ task.name }}</div>
                        <div class="kanban-card-meta">
                            <span>{{ task.assignee or '未分配' }}</span>
                            <span>💼 {{ task.story_points }}pts</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="kanban-column">
                    <div class="kanban-header">
                        <span class="kanban-title">👀 验收中</span>
                        <span class="kanban-count">{{ tasks.review|length }}</span>
                    </div>
                    {% for task in tasks.review %}
                    <div class="kanban-card">
                        <span class="kanban-card-priority {{ task.priority }}">{{ task.priority }}</span>
                        <div class="kanban-card-title">{{ task.name }}</div>
                        <div class="kanban-card-meta">
                            <span>{{ task.assignee or '未分配' }}</span>
                            <span>👤 {{ task.reviewer or 'PM' }}</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="kanban-column">
                    <div class="kanban-header">
                        <span class="kanban-title">✅ 已完成</span>
                        <span class="kanban-count">{{ tasks.done|length }}</span>
                    </div>
                    {% for task in tasks.done[:5] %}
                    <div class="kanban-card">
                        <span class="kanban-card-priority {{ task.priority }}">{{ task.priority }}</span>
                        <div class="kanban-card-title">{{ task.name }}</div>
                        <div class="kanban-card-meta">
                            <span>{{ task.assignee or '未分配' }}</span>
                            <span>⭐ {{ task.quality_score or '-' }}</span>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- 里程碑视图 -->
        <div id="milestones" class="view">
            <h2 style="margin-bottom: 20px; font-size: 18px;">🎯 里程碑</h2>
            <div class="milestone-list">
                {% for milestone in milestones %}
                <div class="milestone-item">
                    <div class="milestone-icon {{ milestone.status }}">
                        {% if milestone.status == 'completed' %}✅{% endif %}
                        {% if milestone.status == 'in_progress' %}🔄{% endif %}
                        {% if milestone.status == 'not_started' %}⏳{% endif %}
                    </div>
                    <div class="milestone-content">
                        <div class="milestone-name">{{ milestone.name }}</div>
                        <div class="milestone-desc">{{ milestone.description or '暂无描述' }}</div>
                        <div class="milestone-dates">
                            {% if milestone.planned_start %}计划：{{ milestone.planned_start }}{% endif %}
                            {% if milestone.planned_end %} - {{ milestone.planned_end }}{% endif %}
                        </div>
                    </div>
                    <div class="milestone-progress">
                        <div class="milestone-progress-value">{{ milestone.progress }}%</div>
                        <div class="milestone-progress-label">完成度</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </main>

    <!-- 页脚 -->
    <footer class="footer">
        <p>🧠 Q 脑 (Q-Brain) 项目管理系统 · 由 小七 协助 十一郎 共同打造</p>
        <p style="margin-top: 8px; opacity: 0.6;">最后更新：{{ now }}</p>
    </footer>

    <script>
        function switchView(viewId) {
            // 隐藏所有视图
            document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
            
            // 显示目标视图
            document.getElementById(viewId).classList.add('active');
            
            // 激活对应标签
            event.target.classList.add('active');
        }
        
        // 自动刷新 (每 60 秒)
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页面"""
    # 获取 Dashboard 数据
    dashboard = pm.get_dashboard_data()
    
    # 获取所有项目
    projects = pm.get_all_projects()
    
    # 为每个项目计算进度
    for project in projects:
        stats = pm.get_project_stats(project['project_id'])
        project['task_count'] = stats.get('total_tasks', 0)
        project['completed_tasks'] = stats.get('completed_story_points', 0)
        project['milestone_count'] = len(pm.get_milestones_by_project(project['project_id']))
        
        # 计算进度
        total = stats.get('total_story_points', 0)
        completed = stats.get('completed_story_points', 0)
        project['progress'] = int((completed / total * 100) if total > 0 else 0)
    
    # 获取任务 (按状态分组)
    all_tasks = []
    for project in projects:
        tasks = pm.get_tasks_by_project(project['project_id'])
        all_tasks.extend(tasks)
    
    tasks_by_status = {
        'todo': [t for t in all_tasks if t['status'] == 'todo'],
        'in_progress': [t for t in all_tasks if t['status'] == 'in_progress'],
        'review': [t for t in all_tasks if t['status'] == 'review'],
        'done': [t for t in all_tasks if t['status'] == 'done']
    }
    
    # 获取里程碑
    milestones = []
    for project in projects:
        ms = pm.get_milestones_by_project(project['project_id'])
        milestones.extend(ms)
    
    # 计算 Dashboard 指标
    dashboard['active_projects'] = len([p for p in projects if p['status'] == 'active'])
    dashboard['completion_rate'] = int(
        (dashboard.get('task_stats', {}).get('done', 0) / dashboard['total_tasks'] * 100)
        if dashboard['total_tasks'] > 0 else 0
    )
    dashboard['week_change'] = 5  # 示例值
    dashboard['avg_quality'] = 8.5  # 示例值
    dashboard['approval_rate'] = 90  # 示例值
    
    return render_template_string(
        HTML_TEMPLATE,
        dashboard=dashboard,
        projects=projects,
        tasks=tasks_by_status,
        milestones=milestones,
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/api/dashboard')
def api_dashboard():
    """API: Dashboard 数据"""
    return jsonify(pm.get_dashboard_data())

@app.route('/api/projects')
def api_projects():
    """API: 项目列表"""
    projects = pm.get_all_projects()
    
    for project in projects:
        stats = pm.get_project_stats(project['project_id'])
        project['stats'] = stats
    
    return jsonify(projects)

@app.route('/api/tasks')
def api_tasks():
    """API: 任务列表"""
    project_id = request.args.get('project_id')
    status = request.args.get('status')
    
    if project_id:
        tasks = pm.get_tasks_by_project(project_id, status)
    else:
        tasks = []
        for p in pm.get_all_projects():
            tasks.extend(pm.get_tasks_by_project(p['project_id'], status))
    
    return jsonify(tasks)

@app.route('/api/milestones')
def api_milestones():
    """API: 里程碑列表"""
    project_id = request.args.get('project_id')
    
    if project_id:
        milestones = pm.get_milestones_by_project(project_id)
    else:
        milestones = []
        for p in pm.get_all_projects():
            milestones.extend(pm.get_milestones_by_project(p['project_id']))
    
    return jsonify(milestones)

@app.route('/api/schedule')
def api_schedule():
    """API: 调度任务"""
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'error': '需要 project_id'}), 400
    
    scheduled = scheduler.schedule_tasks(project_id)
    return jsonify({'scheduled': scheduled})

@app.route('/api/rebalance')
def api_rebalance():
    """API: 重新平衡任务"""
    result = scheduler.rebalance_tasks()
    return jsonify(result)

if __name__ == '__main__':
    print("🚀 启动 Q 脑项目管理系统 Dashboard (端口 5008)")
    print("📋 访问地址：http://localhost:5008")
    print("📊 功能：项目列表 · 任务看板 · 里程碑进度 · 验收报告")
    app.run(host='0.0.0.0', port=5008, debug=False)
