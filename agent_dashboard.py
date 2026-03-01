"""
Agent管理Dashboard - 现代化深色主题
Flask + Chart.js + 玻璃拟态设计
端口: 5007
"""
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import random
import json

app = Flask(__name__)

# ============ 模拟数据生成器 ============

def generate_mock_agents():
    """生成模拟Agent状态数据"""
    agents = [
        {
            "id": "agent_001",
            "name": "AlphaTrader",
            "role": "美股策略分析师",
            "status": "running",
            "current_task": "分析AAPL技术指标",
            "task_progress": 65,
            "avatar": "🤖",
            "workload": 78,
            "success_rate": 94.5,
            "avg_response": 245,
            "quality_score": 4.8,
            "tasks_completed_today": 12,
            "last_active": (datetime.now() - timedelta(minutes=2)).strftime('%H:%M:%S')
        },
        {
            "id": "agent_002",
            "name": "BetaWatcher",
            "role": "A股数据监控",
            "status": "idle",
            "current_task": "空闲",
            "task_progress": 0,
            "avatar": "👁️",
            "workload": 23,
            "success_rate": 98.2,
            "avg_response": 189,
            "quality_score": 4.9,
            "tasks_completed_today": 8,
            "last_active": (datetime.now() - timedelta(minutes=15)).strftime('%H:%M:%S')
        },
        {
            "id": "agent_003",
            "name": "GammaRisk",
            "role": "风险管控专员",
            "status": "busy",
            "current_task": "评估组合风险敞口",
            "task_progress": 42,
            "avatar": "🛡️",
            "workload": 91,
            "success_rate": 99.1,
            "avg_response": 312,
            "quality_score": 5.0,
            "tasks_completed_today": 6,
            "last_active": (datetime.now() - timedelta(seconds=30)).strftime('%H:%M:%S')
        },
        {
            "id": "agent_004",
            "name": "DeltaNews",
            "role": "新闻情绪分析",
            "status": "error",
            "current_task": "获取财经新闻流",
            "task_progress": 0,
            "avatar": "📰",
            "workload": 45,
            "success_rate": 87.3,
            "avg_response": 0,
            "quality_score": 4.2,
            "tasks_completed_today": 3,
            "last_active": (datetime.now() - timedelta(minutes=45)).strftime('%H:%M:%S'),
            "error_msg": "API连接超时"
        },
        {
            "id": "agent_005",
            "name": "EpsilonBacktest",
            "role": "回测引擎",
            "status": "running",
            "current_task": "执行多因子回测",
            "task_progress": 78,
            "avatar": "📊",
            "workload": 85,
            "success_rate": 96.7,
            "avg_response": 567,
            "quality_score": 4.7,
            "tasks_completed_today": 4,
            "last_active": (datetime.now() - timedelta(minutes=1)).strftime('%H:%M:%S')
        },
        {
            "id": "agent_006",
            "name": "ZetaNotify",
            "role": "通知推送助手",
            "status": "idle",
            "current_task": "等待新消息",
            "task_progress": 0,
            "avatar": "📢",
            "workload": 12,
            "success_rate": 99.8,
            "avg_response": 89,
            "quality_score": 4.9,
            "tasks_completed_today": 23,
            "last_active": (datetime.now() - timedelta(minutes=5)).strftime('%H:%M:%S')
        }
    ]
    return agents

def generate_tasks():
    """生成今日任务列表"""
    tasks = [
        {
            "id": "task_001",
            "title": "美股早盘扫描",
            "assignee": "AlphaTrader",
            "assignee_id": "agent_001",
            "status": "completed",
            "priority": "high",
            "estimated_time": "09:30",
            "actual_time": "09:25",
            "progress": 100
        },
        {
            "id": "task_002",
            "title": "A股市场开盘监控",
            "assignee": "BetaWatcher",
            "assignee_id": "agent_002",
            "status": "completed",
            "priority": "high",
            "estimated_time": "09:35",
            "actual_time": "09:32",
            "progress": 100
        },
        {
            "id": "task_003",
            "title": "风险评估日报",
            "assignee": "GammaRisk",
            "assignee_id": "agent_003",
            "status": "in_progress",
            "priority": "medium",
            "estimated_time": "11:00",
            "actual_time": None,
            "progress": 60
        },
        {
            "id": "task_004",
            "title": "策略V6回测验证",
            "assignee": "EpsilonBacktest",
            "assignee_id": "agent_005",
            "status": "in_progress",
            "priority": "high",
            "estimated_time": "12:00",
            "actual_time": None,
            "progress": 75
        },
        {
            "id": "task_005",
            "title": "财经新闻摘要",
            "assignee": "DeltaNews",
            "assignee_id": "agent_004",
            "status": "pending",
            "priority": "low",
            "estimated_time": "14:00",
            "actual_time": None,
            "progress": 0
        },
        {
            "id": "task_006",
            "title": "收盘报告生成",
            "assignee": "AlphaTrader",
            "assignee_id": "agent_001",
            "status": "pending",
            "priority": "medium",
            "estimated_time": "16:30",
            "actual_time": None,
            "progress": 0
        },
        {
            "id": "task_007",
            "title": "飞书群组通知",
            "assignee": "ZetaNotify",
            "assignee_id": "agent_006",
            "status": "completed",
            "priority": "low",
            "estimated_time": "10:00",
            "actual_time": "09:58",
            "progress": 100
        }
    ]
    return tasks

def generate_logs():
    """生成实时日志数据"""
    logs = [
        {"time": "11:36:42", "agent": "AlphaTrader", "level": "info", "message": "完成AAPL技术分析，识别买入信号"},
        {"time": "11:35:18", "agent": "GammaRisk", "level": "warning", "message": "检测到组合波动率上升，建议减仓"},
        {"time": "11:34:05", "agent": "EpsilonBacktest", "level": "info", "message": "回测进度: 75% (1524/2031个交易日)"},
        {"time": "11:33:22", "agent": "DeltaNews", "level": "error", "message": "新闻API连接失败: Connection timeout"},
        {"time": "11:32:45", "agent": "BetaWatcher", "level": "info", "message": "A股市场数据同步完成"},
        {"time": "11:31:30", "agent": "ZetaNotify", "level": "info", "message": "发送飞书通知: 风险告警"},
        {"time": "11:30:15", "agent": "AlphaTrader", "level": "info", "message": "开始扫描纳斯达克成分股"},
        {"time": "11:28:42", "agent": "GammaRisk", "level": "info", "message": "重新计算VaR值: 2.3%"},
        {"time": "11:27:20", "agent": "DeltaNews", "level": "warning", "message": "重试获取新闻数据 (第3次)"},
        {"time": "11:25:00", "agent": "EpsilonBacktest", "level": "info", "message": "加载历史数据: 2015-2024"},
        {"time": "11:24:18", "agent": "BetaWatcher", "level": "info", "message": "监控股票池更新: 50只活跃股票"},
        {"time": "11:22:33", "agent": "ZetaNotify", "level": "info", "message": "系统状态正常，无异常告警"},
    ]
    return logs

def generate_performance_data(agent_id):
    """生成Agent性能历史数据"""
    days = 30
    data = []
    base_date = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        date = base_date + timedelta(days=i)
        data.append({
            "date": date.strftime('%m-%d'),
            "tasks_completed": random.randint(3, 15),
            "success_rate": round(random.uniform(85, 100), 1),
            "avg_response": random.randint(100, 600),
            "quality_score": round(random.uniform(4.0, 5.0), 1)
        })
    
    return data

# ============ 路由 ============

@app.route('/')
def index():
    """主页面"""
    agents = generate_mock_agents()
    tasks = generate_tasks()
    logs = generate_logs()
    
    # 统计数据
    total_agents = len(agents)
    running_agents = sum(1 for a in agents if a['status'] == 'running')
    idle_agents = sum(1 for a in agents if a['status'] == 'idle')
    busy_agents = sum(1 for a in agents if a['status'] == 'busy')
    error_agents = sum(1 for a in agents if a['status'] == 'error')
    
    completed_tasks = sum(1 for t in tasks if t['status'] == 'completed')
    in_progress_tasks = sum(1 for t in tasks if t['status'] == 'in_progress')
    pending_tasks = sum(1 for t in tasks if t['status'] == 'pending')
    
    stats = {
        "total_agents": total_agents,
        "running": running_agents,
        "idle": idle_agents,
        "busy": busy_agents,
        "error": error_agents,
        "total_tasks": len(tasks),
        "completed": completed_tasks,
        "in_progress": in_progress_tasks,
        "pending": pending_tasks,
        "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return render_template_string(HTML,
        agents=agents,
        tasks=tasks,
        logs=logs,
        stats=stats
    )

@app.route('/api/status')
def api_status():
    """API: 获取当前状态"""
    agents = generate_mock_agents()
    tasks = generate_tasks()
    
    stats = {
        "total_agents": len(agents),
        "running": sum(1 for a in agents if a['status'] == 'running'),
        "idle": sum(1 for a in agents if a['status'] == 'idle'),
        "busy": sum(1 for a in agents if a['status'] == 'busy'),
        "error": sum(1 for a in agents if a['status'] == 'error'),
        "total_tasks": len(tasks),
        "completed": sum(1 for t in tasks if t['status'] == 'completed'),
        "in_progress": sum(1 for t in tasks if t['status'] == 'in_progress'),
        "pending": sum(1 for t in tasks if t['status'] == 'pending'),
        "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify({
        "agents": agents,
        "tasks": tasks,
        "stats": stats
    })

@app.route('/api/logs')
def api_logs():
    """API: 获取日志数据"""
    agent_filter = request.args.get('agent', 'all')
    level_filter = request.args.get('level', 'all')
    
    logs = generate_logs()
    
    if agent_filter != 'all':
        logs = [l for l in logs if l['agent'] == agent_filter]
    if level_filter != 'all':
        logs = [l for l in logs if l['level'] == level_filter]
    
    return jsonify({"logs": logs})

@app.route('/api/agent/<agent_id>/performance')
def api_agent_performance(agent_id):
    """API: 获取Agent性能数据"""
    history = generate_performance_data(agent_id)
    return jsonify({
        "agent_id": agent_id,
        "history": history
    })

# ============ HTML模板 ============

HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Management Dashboard | Agent管理系统</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
            background-image: 
                radial-gradient(ellipse at 20% 20%, rgba(139, 92, 246, 0.15) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(6, 182, 212, 0.1) 0%, transparent 50%);
        }
        
        .container { max-width: 1600px; margin: 0 auto; padding: 24px; }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            padding: 20px 24px;
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
        }
        
        .header-title h1 {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 4px;
        }
        
        .header-title p {
            color: var(--text-secondary);
            font-size: 14px;
        }
        
        .header-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(139, 92, 246, 0.3);
        }
        
        .refresh-btn.spinning {
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .auto-refresh-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: rgba(6, 182, 212, 0.1);
            border: 1px solid rgba(6, 182, 212, 0.3);
            border-radius: 8px;
            font-size: 13px;
            color: var(--accent-cyan);
        }
        
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-cyan);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        
        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            position: relative;
            overflow: hidden;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .stat-card:hover::before { opacity: 1; }
        
        .stat-card.running::before { background: linear-gradient(90deg, var(--accent-green), #34d399); }
        .stat-card.idle::before { background: linear-gradient(90deg, var(--accent-blue), #60a5fa); }
        .stat-card.busy::before { background: linear-gradient(90deg, var(--accent-yellow), #fbbf24); }
        .stat-card.error::before { background: linear-gradient(90deg, var(--accent-red), #f87171); }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        
        .stat-value.small {
            font-size: 24px;
        }
        
        .stat-change {
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .positive { color: var(--accent-green); }
        .negative { color: var(--accent-red); }
        .warning { color: var(--accent-yellow); }
        .info { color: var(--accent-blue); }
        
        /* Main Content Grid */
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }
        
        @media (max-width: 1200px) {
            .main-grid { grid-template-columns: 1fr; }
        }
        
        /* Section Title */
        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* Agent Cards */
        .agents-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }
        
        .agent-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        
        .agent-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            border-color: rgba(139, 92, 246, 0.3);
        }
        
        .agent-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            opacity: 0.8;
        }
        
        .agent-card.running::before { background: var(--accent-green); }
        .agent-card.idle::before { background: var(--accent-blue); }
        .agent-card.busy::before { background: var(--accent-yellow); }
        .agent-card.error::before { background: var(--accent-red); }
        
        .agent-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
        }
        
        .agent-avatar {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .agent-info h3 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 2px;
        }
        
        .agent-info p {
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 500;
            margin-left: auto;
        }
        
        .status-badge.running {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
        }
        
        .status-badge.idle {
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
        }
        
        .status-badge.busy {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-yellow);
        }
        
        .status-badge.error {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
        }
        
        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .agent-task {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 12px;
        }
        
        .task-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        
        .task-name {
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 8px;
        }
        
        .progress-bar {
            height: 4px;
            background: rgba(75, 85, 99, 0.3);
            border-radius: 2px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 2px;
            transition: width 0.3s;
        }
        
        .progress-fill.running { background: var(--accent-green); }
        .progress-fill.busy { background: var(--accent-yellow); }
        .progress-fill.error { background: var(--accent-red); }
        .progress-fill.idle { background: var(--accent-blue); }
        
        .agent-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            font-size: 12px;
        }
        
        .agent-stat {
            text-align: center;
        }
        
        .agent-stat-value {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 2px;
        }
        
        .agent-stat-label {
            color: var(--text-secondary);
            font-size: 10px;
        }
        
        /* Task Board */
        .task-board {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
        }
        
        .task-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }
        
        .task-tab {
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            background: rgba(255, 255, 255, 0.03);
            border: none;
            color: var(--text-secondary);
        }
        
        .task-tab:hover {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-primary);
        }
        
        .task-tab.active {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            color: white;
        }
        
        .task-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .task-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 8px;
            background: rgba(255, 255, 255, 0.02);
            transition: background 0.2s;
        }
        
        .task-item:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .task-status-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        
        .task-status-icon.completed { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }
        .task-status-icon.in_progress { background: rgba(245, 158, 11, 0.15); color: var(--accent-yellow); }
        .task-status-icon.pending { background: rgba(107, 114, 128, 0.15); color: var(--text-secondary); }
        
        .task-content {
            flex: 1;
        }
        
        .task-title {
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 2px;
        }
        
        .task-meta {
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .task-assignee {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: rgba(139, 92, 246, 0.1);
            border-radius: 20px;
            font-size: 12px;
        }
        
        .task-time {
            font-size: 12px;
            color: var(--text-secondary);
            min-width: 50px;
            text-align: right;
        }
        
        /* Performance Section */
        .performance-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }
        
        @media (max-width: 1200px) {
            .performance-section { grid-template-columns: 1fr; }
        }
        
        .performance-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
        }
        
        .chart-container {
            position: relative;
            height: 250px;
            margin-top: 16px;
        }
        
        /* Log Viewer */
        .log-viewer {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
        }
        
        .log-filters {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        
        .log-filter {
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .log-filter:hover, .log-filter.active {
            background: rgba(139, 92, 246, 0.2);
            border-color: var(--accent-purple);
            color: var(--text-primary);
        }
        
        .log-stream {
            max-height: 300px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 12px;
            line-height: 1.6;
        }
        
        .log-entry {
            display: flex;
            gap: 12px;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 4px;
        }
        
        .log-entry:hover {
            background: rgba(255, 255, 255, 0.03);
        }
        
        .log-time {
            color: var(--text-secondary);
            min-width: 70px;
        }
        
        .log-agent {
            color: var(--accent-cyan);
            min-width: 100px;
        }
        
        .log-level {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            min-width: 50px;
            text-align: center;
        }
        
        .log-level.info {
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
        }
        
        .log-level.warning {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-yellow);
        }
        
        .log-level.error {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
        }
        
        .log-message {
            flex: 1;
            color: var(--text-primary);
        }
        
        .log-message.error {
            color: var(--accent-red);
        }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .modal-overlay.active { display: flex; }
        
        .modal {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 32px;
            width: 90%;
            max-width: 900px;
            max-height: 85vh;
            overflow-y: auto;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        
        .modal-title {
            font-size: 20px;
            font-weight: 600;
        }
        
        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
            padding: 4px;
        }
        
        .modal-close:hover { color: var(--text-primary); }
        
        .agent-detail-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .detail-stat {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        
        .detail-stat-value {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        
        .detail-stat-label {
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 24px;
            color: var(--text-secondary);
            font-size: 13px;
        }
        
        .last-update {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-title">
                <h1>🤖 Agent Management Dashboard</h1>
                <p>Agent管理系统 | 实时监控所有Agent状态与工作情况</p>
            </div>
            <div class="header-actions">
                <div class="auto-refresh-indicator">
                    <span class="pulse-dot"></span>
                    <span>自动刷新中 (30s)</span>
                </div>
                <button class="refresh-btn" onclick="manualRefresh()" id="refreshBtn">
                    🔄 刷新
                </button>
            </div>
        </div>
        
        <!-- Stats Overview -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">🤖 总Agent数</div>
                <div class="stat-value" id="stat-total">{{ stats.total_agents }}</div>
                <div class="stat-change" style="color: var(--text-secondary);">活跃智能体</div>
            </div>
            <div class="stat-card running">
                <div class="stat-label">▶️ 运行中</div>
                <div class="stat-value positive" id="stat-running">{{ stats.running }}</div>
                <div class="stat-change positive">正常工作</div>
            </div>
            <div class="stat-card idle">
                <div class="stat-label">⏸️ 空闲中</div>
                <div class="stat-value info" id="stat-idle">{{ stats.idle }}</div>
                <div class="stat-change info">等待任务</div>
            </div>
            <div class="stat-card busy">
                <div class="stat-label">⚡ 忙碌中</div>
                <div class="stat-value warning" id="stat-busy">{{ stats.busy }}</div>
                <div class="stat-change warning">高负载</div>
            </div>
            <div class="stat-card error">
                <div class="stat-label">❌ 异常</div>
                <div class="stat-value negative" id="stat-error">{{ stats.error }}</div>
                <div class="stat-change negative">需要关注</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📋 今日任务</div>
                <div class="stat-value small" id="stat-tasks">{{ stats.total_tasks }}</div>
                <div class="stat-change" style="color: var(--text-secondary);">
                    <span class="positive">{{ stats.completed }}完成</span> / 
                    <span class="warning">{{ stats.in_progress }}进行中</span>
                </div>
            </div>
        </div>
        
        <!-- Main Content Grid -->
        <div class="main-grid">
            <!-- Agent Overview -->
            <div>
                <div class="section-title">🤖 Agent总览</div>
                <div class="agents-grid" id="agents-grid">
                    {% for agent in agents %}
                    <div class="agent-card {{ agent.status }}" onclick="showAgentDetail('{{ agent.id }}')">
                        <div class="agent-header">
                            <div class="agent-avatar">{{ agent.avatar }}</div>
                            <div class="agent-info">
                                <h3>{{ agent.name }}</h3>
                                <p>{{ agent.role }}</p>
                            </div>
                            <span class="status-badge {{ agent.status }}">
                                <span class="status-dot"></span>
                                {{ '运行中' if agent.status == 'running' else '空闲' if agent.status == 'idle' else '忙碌' if agent.status == 'busy' else '错误' }}
                            </span>
                        </div>
                        <div class="agent-task">
                            <div class="task-label">当前任务</div>
                            <div class="task-name">{{ agent.current_task }}</div>
                            <div class="progress-bar">
                                <div class="progress-fill {{ agent.status }}" style="width: {{ agent.task_progress }}%;"></div>
                            </div>
                        </div>
                        <div class="agent-stats">
                            <div class="agent-stat">
                                <div class="agent-stat-value">{{ agent.tasks_completed_today }}</div>
                                <div class="agent-stat-label">今日完成</div>
                            </div>
                            <div class="agent-stat">
                                <div class="agent-stat-value">{{ agent.success_rate }}%</div>
                                <div class="agent-stat-label">成功率</div>
                            </div>
                            <div class="agent-stat">
                                <div class="agent-stat-value">{{ agent.avg_response }}ms</div>
                                <div class="agent-stat-label">响应时间</div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Task Board -->
            <div>
                <div class="section-title">📋 工作看板</div>
                <div class="task-board">
                    <div class="task-tabs">
                        <button class="task-tab active" onclick="filterTasks('all')">全部 ({{ stats.total_tasks }})</button>
                        <button class="task-tab" onclick="filterTasks('in_progress')">进行中 ({{ stats.in_progress }})</button>
                        <button class="task-tab" onclick="filterTasks('completed')">已完成 ({{ stats.completed }})</button>
                        <button class="task-tab" onclick="filterTasks('pending')">待处理 ({{ stats.pending }})</button>
                    </div>
                    <div class="task-list" id="task-list">
                        {% for task in tasks %}
                        <div class="task-item" data-status="{{ task.status }}">
                            <div class="task-status-icon {{ task.status }}">
                                {{ '✓' if task.status == 'completed' else '⟳' if task.status == 'in_progress' else '○' }}
                            </div>
                            <div class="task-content">
                                <div class="task-title">{{ task.title }}</div>
                                <div class="task-meta">
                                    优先级: {{ '高' if task.priority == 'high' else '中' if task.priority == 'medium' else '低' }} | 
                                    进度: {{ task.progress }}%
                                </div>
                            </div>
                            <div class="task-assignee">👤 {{ task.assignee }}</div>
                            <div class="task-time">{{ task.estimated_time }}</div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Performance Section -->
        <div class="performance-section">
            <div class="performance-card">
                <div class="section-title">📊 Agent工作量统计 (30天)</div>
                <div class="chart-container">
                    <canvas id="workloadChart"></canvas>
                </div>
            </div>
            <div class="performance-card">
                <div class="section-title">🎯 任务完成率趋势</div>
                <div class="chart-container">
                    <canvas id="successRateChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Log Viewer -->
        <div class="log-viewer">
            <div class="section-title">📜 实时日志</div>
            <div class="log-filters">
                <span class="log-filter active" onclick="filterLogs('all')">全部</span>
                <span class="log-filter" onclick="filterLogs('info')">ℹ️ Info</span>
                <span class="log-filter" onclick="filterLogs('warning')">⚠️ Warning</span>
                <span class="log-filter" onclick="filterLogs('error')">❌ Error</span>
                <span style="flex: 1;"></span>
                <select class="log-filter" id="agentFilter" onchange="filterByAgent()">
                    <option value="all">所有Agent</option>
                    {% for agent in agents %}
                    <option value="{{ agent.name }}">{{ agent.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="log-stream" id="log-stream">
                {% for log in logs %}
                <div class="log-entry" data-level="{{ log.level }}" data-agent="{{ log.agent }}">
                    <span class="log-time">{{ log.time }}</span>
                    <span class="log-agent">{{ log.agent }}</span>
                    <span class="log-level {{ log.level }}">{{ log.level }}</span>
                    <span class="log-message {{ log.level }}">{{ log.message }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="last-update">
                <span>⏱️ 最后更新:</span>
                <span id="last-update-time">{{ stats.last_update }}</span>
            </div>
        </div>
    </div>
    
    <!-- Agent Detail Modal -->
    <div class="modal-overlay" id="agentModal" onclick="closeModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title" id="modalTitle">Agent详情</div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="agent-detail-grid" id="agentDetailGrid">
                <!-- Dynamic content -->
            </div>
            <div class="chart-container">
                <canvas id="agentPerformanceChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        let workloadChart = null;
        let successRateChart = null;
        let agentPerformanceChart = null;
        let autoRefreshInterval = null;
        
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            startAutoRefresh();
        });
        
        // 初始化图表
        function initCharts() {
            // 工作量图表
            const workloadCtx = document.getElementById('workloadChart').getContext('2d');
            workloadChart = new Chart(workloadCtx, {
                type: 'bar',
                data: {
                    labels: ['AlphaTrader', 'BetaWatcher', 'GammaRisk', 'DeltaNews', 'EpsilonBacktest', 'ZetaNotify'],
                    datasets: [{
                        label: '完成任务数',
                        data: [156, 89, 67, 45, 34, 234],
                        backgroundColor: [
                            'rgba(6, 182, 212, 0.8)',
                            'rgba(139, 92, 246, 0.8)',
                            'rgba(16, 185, 129, 0.8)',
                            'rgba(239, 68, 68, 0.8)',
                            'rgba(245, 158, 11, 0.8)',
                            'rgba(59, 130, 246, 0.8)'
                        ],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#9ca3af', font: { size: 11 } } },
                        y: { grid: { color: 'rgba(75, 85, 99, 0.2)' }, ticks: { color: '#9ca3af' } }
                    }
                }
            });
            
            // 成功率图表
            const successCtx = document.getElementById('successRateChart').getContext('2d');
            successRateChart = new Chart(successCtx, {
                type: 'line',
                data: {
                    labels: ['01-01', '01-05', '01-10', '01-15', '01-20', '01-25', '01-30'],
                    datasets: [{
                        label: '平均成功率',
                        data: [92.5, 94.2, 93.8, 95.1, 94.7, 96.2, 95.8],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#10b981',
                        pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(75, 85, 99, 0.2)' }, ticks: { color: '#9ca3af' } },
                        y: { 
                            grid: { color: 'rgba(75, 85, 99, 0.2)' }, 
                            ticks: { color: '#9ca3af' },
                            min: 85,
                            max: 100
                        }
                    }
                }
            });
        }
        
        // 自动刷新
        function startAutoRefresh() {
            autoRefreshInterval = setInterval(() => {
                fetchStatus();
            }, 30000);
        }
        
        // 手动刷新
        function manualRefresh() {
            const btn = document.getElementById('refreshBtn');
            btn.classList.add('spinning');
            btn.disabled = true;
            
            fetchStatus().then(() => {
                setTimeout(() => {
                    btn.classList.remove('spinning');
                    btn.disabled = false;
                }, 500);
            });
        }
        
        // 获取状态数据
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateUI(data);
            } catch (error) {
                console.error('Failed to fetch status:', error);
            }
        }
        
        // 更新UI
        function updateUI(data) {
            // 更新统计卡片
            document.getElementById('stat-total').textContent = data.stats.total_agents;
            document.getElementById('stat-running').textContent = data.stats.running;
            document.getElementById('stat-idle').textContent = data.stats.idle;
            document.getElementById('stat-busy').textContent = data.stats.busy;
            document.getElementById('stat-error').textContent = data.stats.error;
            document.getElementById('stat-tasks').textContent = data.stats.total_tasks;
            
            // 更新时间
            document.getElementById('last-update-time').textContent = data.stats.last_update;
        }
        
        // 显示Agent详情
        async function showAgentDetail(agentId) {
            const modal = document.getElementById('agentModal');
            const title = document.getElementById('modalTitle');
            const detailGrid = document.getElementById('agentDetailGrid');
            
            title.textContent = `Agent详情 - ${agentId}`;
            
            // 模拟详情数据
            detailGrid.innerHTML = `
                <div class="detail-stat">
                    <div class="detail-stat-value positive">94.5%</div>
                    <div class="detail-stat-label">成功率</div>
                </div>
                <div class="detail-stat">
                    <div class="detail-stat-value info">245ms</div>
                    <div class="detail-stat-label">平均响应</div>
                </div>
                <div class="detail-stat">
                    <div class="detail-stat-value warning">4.8</div>
                    <div class="detail-stat-label">质量评分</div>
                </div>
                <div class="detail-stat">
                    <div class="detail-stat-value">156</div>
                    <div class="detail-stat-label">本月任务</div>
                </div>
            `;
            
            modal.classList.add('active');
            
            // 渲染性能图表
            setTimeout(() => {
                renderAgentPerformanceChart();
            }, 100);
        }
        
        // 渲染Agent性能图表
        function renderAgentPerformanceChart() {
            const ctx = document.getElementById('agentPerformanceChart').getContext('2d');
            
            if (agentPerformanceChart) {
                agentPerformanceChart.destroy();
            }
            
            agentPerformanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['01-01', '01-05', '01-10', '01-15', '01-20', '01-25', '01-30'],
                    datasets: [{
                        label: '任务完成数',
                        data: [5, 8, 12, 7, 10, 15, 12],
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y'
                    }, {
                        label: '质量评分',
                        data: [4.5, 4.6, 4.8, 4.7, 4.9, 4.8, 4.8],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        tension: 0.4,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        x: { grid: { color: 'rgba(75, 85, 99, 0.2)' }, ticks: { color: '#9ca3af' } },
                        y: { 
                            type: 'linear',
                            display: true,
                            position: 'left',
                            grid: { color: 'rgba(75, 85, 99, 0.2)' },
                            ticks: { color: '#9ca3af' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            ticks: { color: '#8b5cf6', min: 0, max: 5 }
                        }
                    }
                }
            });
        }
        
        // 关闭模态框
        function closeModal(event) {
            if (!event || event.target.id === 'agentModal') {
                document.getElementById('agentModal').classList.remove('active');
            }
        }
        
        // 任务筛选
        function filterTasks(status) {
            // 更新标签样式
            document.querySelectorAll('.task-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // 筛选任务
            const tasks = document.querySelectorAll('#task-list .task-item');
            tasks.forEach(task => {
                if (status === 'all' || task.dataset.status === status) {
                    task.style.display = 'flex';
                } else {
                    task.style.display = 'none';
                }
            });
        }
        
        // 日志筛选
        function filterLogs(level) {
            // 更新筛选器样式
            document.querySelectorAll('.log-filter').forEach(filter => {
                filter.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // 筛选日志
            const logs = document.querySelectorAll('#log-stream .log-entry');
            logs.forEach(log => {
                if (level === 'all' || log.dataset.level === level) {
                    log.style.display = 'flex';
                } else {
                    log.style.display = 'none';
                }
            });
        }
        
        // 按Agent筛选日志
        function filterByAgent() {
            const agent = document.getElementById('agentFilter').value;
            const logs = document.querySelectorAll('#log-stream .log-entry');
            
            logs.forEach(log => {
                if (agent === 'all' || log.dataset.agent === agent) {
                    log.style.display = 'flex';
                } else {
                    log.style.display = 'none';
                }
            });
        }
        
        // ESC键关闭模态框
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeModal();
            }
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("🚀 启动Agent管理Dashboard (端口 5007)")
    print("🤖 访问地址: http://localhost:5007")
    app.run(host='0.0.0.0', port=5007, debug=False)
