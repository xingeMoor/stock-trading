"""
Q脑 Agent 管理 Dashboard V2
连接真实 Agent 数据库 + OpenClaw Subagents 同步
端口：5007

功能:
- 显示 Agent 实时状态 (idle/running/completed/error)
- 显示使用的模型 (如 bailian/qwen3.5-plus)
- 显示当前任务名称
- 显示运行时长
- 显示最后活跃时间
"""
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stock-trading', 'src'))
from agent_manager import (
    get_all_agents, get_dashboard_stats, get_agent_tasks,
    init_agent_db, sync_openclaw_agents, AGENT_INFO
)

app = Flask(__name__)

# 初始化数据库
init_agent_db()

# ============ HTML 模板 ============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q脑 Agent 管理系统 | Q-Brain Agent Dashboard</title>
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
        }
        
        /* 头部 */
        .header {
            background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(139, 92, 246, 0.1));
            border-bottom: 1px solid var(--border);
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
        }
        
        .logo-text h1 {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .logo-text p {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }
        
        .header-stats {
            display: flex;
            gap: 30px;
        }
        
        .header-stat {
            text-align: right;
        }
        
        .header-stat-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--accent-cyan);
        }
        
        .header-stat-label {
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        /* 同步按钮 */
        .sync-btn {
            background: linear-gradient(135deg, var(--accent-green), var(--accent-cyan));
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .sync-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        
        .sync-btn.syncing {
            animation: pulse 1s infinite;
        }
        
        /* 主内容区 */
        .main-container {
            padding: 30px 40px;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* 统计卡片 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(6, 182, 212, 0.1);
        }
        
        .stat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .stat-title {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .stat-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        
        .stat-icon.cyan { background: rgba(6, 182, 212, 0.2); }
        .stat-icon.purple { background: rgba(139, 92, 246, 0.2); }
        .stat-icon.green { background: rgba(16, 185, 129, 0.2); }
        .stat-icon.yellow { background: rgba(245, 158, 11, 0.2); }
        .stat-icon.blue { background: rgba(59, 130, 246, 0.2); }
        
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .stat-change {
            font-size: 13px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .stat-change.positive { color: var(--accent-green); }
        .stat-change.negative { color: var(--accent-red); }
        
        .model-tag {
            display: inline-block;
            background: rgba(139, 92, 246, 0.2);
            color: var(--accent-purple);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-top: 4px;
        }
        
        /* Agent 层级分布 */
        .layer-section {
            margin-bottom: 30px;
        }
        
        .layer-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }
        
        .layer-icon {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        
        .layer-title {
            font-size: 18px;
            font-weight: 600;
        }
        
        .layer-count {
            margin-left: auto;
            background: var(--bg-secondary);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        /* Agent 卡片网格 */
        .agent-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }
        
        .agent-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(10px);
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
            cursor: pointer;
        }
        
        .agent-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--status-color, var(--accent-green));
        }
        
        .agent-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .agent-card.running { --status-color: var(--accent-green); }
        .agent-card.idle { --status-color: var(--accent-blue); }
        .agent-card.completed { --status-color: var(--accent-cyan); }
        .agent-card.error { --status-color: var(--accent-red); }
        .agent-card.offline { --status-color: var(--text-secondary); }
        
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
            background: var(--bg-secondary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
        }
        
        .agent-info h3 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .agent-role {
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .agent-status {
            margin-left: auto;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .agent-status.running {
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
        }
        
        .agent-status.idle {
            background: rgba(59, 130, 246, 0.2);
            color: var(--accent-blue);
        }
        
        .agent-status.completed {
            background: rgba(6, 182, 212, 0.2);
            color: var(--accent-cyan);
        }
        
        .agent-status.error {
            background: rgba(239, 68, 68, 0.2);
            color: var(--accent-red);
        }
        
        .agent-task {
            background: var(--bg-secondary);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 16px;
        }
        
        .task-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }
        
        .task-name {
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 8px;
        }
        
        .agent-details {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-bottom: 12px;
        }
        
        .detail-item {
            background: var(--bg-secondary);
            border-radius: 6px;
            padding: 8px;
        }
        
        .detail-label {
            font-size: 10px;
            color: var(--text-secondary);
            margin-bottom: 2px;
        }
        
        .detail-value {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .agent-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }
        
        .metric {
            text-align: center;
        }
        
        .metric-value {
            font-size: 18px;
            font-weight: 700;
            color: var(--accent-cyan);
        }
        
        .metric-label {
            font-size: 10px;
            color: var(--text-secondary);
            margin-top: 2px;
        }
        
        /* 任务列表 */
        .tasks-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-top: 30px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 18px;
            font-weight: 600;
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: opacity 0.3s;
        }
        
        .refresh-btn:hover {
            opacity: 0.9;
        }
        
        .task-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .task-item {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px;
            background: var(--bg-secondary);
            border-radius: 12px;
            transition: background 0.3s;
        }
        
        .task-item:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .task-agent {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background: var(--bg-card);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        
        .task-content {
            flex: 1;
        }
        
        .task-title {
            font-weight: 500;
            margin-bottom: 4px;
        }
        
        .task-meta {
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            gap: 12px;
        }
        
        .task-model {
            color: var(--accent-purple);
        }
        
        .task-priority {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        
        .task-priority.high {
            background: rgba(239, 68, 68, 0.2);
            color: var(--accent-red);
        }
        
        .task-priority.medium {
            background: rgba(245, 158, 11, 0.2);
            color: var(--accent-yellow);
        }
        
        .task-status-badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        
        .task-status-badge.running {
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
        }
        
        .task-status-badge.completed {
            background: rgba(6, 182, 212, 0.2);
            color: var(--accent-cyan);
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
        
        /* 动画 */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .spinner {
            animation: spin 1s linear infinite;
        }
        
        /* 详情弹窗 */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .modal-overlay.active {
            display: flex;
        }
        
        .modal-content {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        }
        
        .modal-close {
            position: absolute;
            top: 15px;
            right: 15px;
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
        }
        
        .modal-close:hover {
            color: var(--text-primary);
        }
        
        .modal-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
        }
        
        .modal-avatar {
            width: 60px;
            height: 60px;
            border-radius: 12px;
            background: var(--bg-card);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
        }
        
        .modal-title h2 {
            font-size: 20px;
            margin-bottom: 4px;
        }
        
        .modal-title p {
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        .config-section {
            margin-bottom: 20px;
        }
        
        .config-section h3 {
            font-size: 14px;
            color: var(--accent-cyan);
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .config-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
        }
        
        .config-item:last-child {
            border-bottom: none;
        }
        
        .config-label {
            color: var(--text-secondary);
            font-size: 13px;
        }
        
        .config-value {
            font-weight: 500;
            font-size: 13px;
        }
        
        .history-list {
            max-height: 200px;
            overflow-y: auto;
        }
        
        .history-item {
            padding: 10px;
            background: var(--bg-card);
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 13px;
        }
        
        .history-time {
            color: var(--text-secondary);
            font-size: 11px;
            margin-bottom: 4px;
        }
    </style>
</head>
<body>
    <!-- 头部 -->
    <header class="header">
        <div class="logo">
            <div class="logo-icon">🧠</div>
            <div class="logo-text">
                <h1>Q 脑 Agent 管理系统</h1>
                <p>Q-Brain Quantitative Trading System</p>
            </div>
        </div>
        <div class="header-stats">
            <div class="header-stat">
                <div class="header-stat-value">{{ stats.total_agents }}</div>
                <div class="header-stat-label">总 Agent 数</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value" style="color: var(--accent-green);">{{ stats.active_agents }}</div>
                <div class="header-stat-label">运行中</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value" style="color: var(--accent-blue);">{{ stats.idle_agents }}</div>
                <div class="header-stat-label">空闲</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value" style="color: var(--accent-red);">{{ stats.error_agents }}</div>
                <div class="header-stat-label">异常</div>
            </div>
        </div>
        <button class="sync-btn" id="syncBtn" onclick="syncAgents()">
            <span>🔄</span> 同步 OpenClaw 状态
        </button>
    </header>

    <!-- 主内容 -->
    <main class="main-container">
        <!-- 统计卡片 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-title">工程层 Agents</span>
                    <div class="stat-icon cyan">🔧</div>
                </div>
                <div class="stat-value" style="color: var(--accent-cyan);">{{ layers.get('工程层', 0) }}</div>
                <div class="stat-change positive">Archie · Dev · Testy · Pixel</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-title">金融层 Agents</span>
                    <div class="stat-icon purple">📈</div>
                </div>
                <div class="stat-value" style="color: var(--accent-purple);">{{ layers.get('金融层', 0) }}</div>
                <div class="stat-change positive">Factor · Senti · Funda · Trader · Risk · Guard</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-title">桥梁层 Agents</span>
                    <div class="stat-icon yellow">🌉</div>
                </div>
                <div class="stat-value" style="color: var(--accent-yellow);">{{ layers.get('桥梁层', 0) }}</div>
                <div class="stat-change positive">Backer · Strategist</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-title">管理层 Agents</span>
                    <div class="stat-icon green">👁️</div>
                </div>
                <div class="stat-value" style="color: var(--accent-green);">{{ layers.get('管理层', 0) }}</div>
                <div class="stat-change positive">PM · Ops</div>
            </div>
            {% if stats.model_distribution %}
            <div class="stat-card">
                <div class="stat-header">
                    <span class="stat-title">模型分布</span>
                    <div class="stat-icon blue">🤖</div>
                </div>
                <div class="stat-value" style="color: var(--accent-blue);">{{ stats.model_distribution|length }}</div>
                <div class="stat-change">
                    {% for model, count in stats.model_distribution.items() %}
                    <span class="model-tag">{{ model }}: {{ count }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>

        <!-- Agent 层级展示 -->
        {% for layer_name, layer_agents in agents_by_layer.items() %}
        <section class="layer-section">
            <div class="layer-header">
                <div class="layer-icon" style="background: 
                    {% if layer_name == '工程层' %}rgba(6, 182, 212, 0.2){% endif %}
                    {% if layer_name == '金融层' %}rgba(139, 92, 246, 0.2){% endif %}
                    {% if layer_name == '桥梁层' %}rgba(245, 158, 11, 0.2){% endif %}
                    {% if layer_name == '管理层' %}rgba(16, 185, 129, 0.2){% endif %}
                ;">
                    {% if layer_name == '工程层' %}🔧{% endif %}
                    {% if layer_name == '金融层' %}📈{% endif %}
                    {% if layer_name == '桥梁层' %}🌉{% endif %}
                    {% if layer_name == '管理层' %}👁️{% endif %}
                </div>
                <h2 class="layer-title">{{ layer_name }}</h2>
                <span class="layer-count">{{ layer_agents|length }} 个 Agent</span>
            </div>
            <div class="agent-grid">
                {% for agent in layer_agents %}
                <div class="agent-card {{ agent.status }}" onclick="showAgentDetails('{{ agent.agent_id }}')">
                    <div class="agent-header">
                        <div class="agent-avatar">{{ agent.emoji }}</div>
                        <div class="agent-info">
                            <h3>{{ agent.name }}</h3>
                            <span class="agent-role">{{ agent.description }}</span>
                        </div>
                        <span class="agent-status {{ agent.status }}">{{ agent.status }}</span>
                    </div>
                    <div class="agent-task">
                        <div class="task-label">当前任务</div>
                        <div class="task-name">{{ agent.current_task or '等待分配任务' }}</div>
                    </div>
                    <div class="agent-details">
                        <div class="detail-item">
                            <div class="detail-label">🤖 模型</div>
                            <div class="detail-value">{{ agent.model }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">⏱️ 运行时长</div>
                            <div class="detail-value">{{ agent.running_duration }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">🕐 最后活跃</div>
                            <div class="detail-value">{{ (agent.last_active[:16] if agent.last_active else 'N/A').replace('T', ' ') }}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">📊 状态</div>
                            <div class="detail-value">{{ agent.status }}</div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>
        {% endfor %}

        <!-- 任务列表 -->
        <section class="tasks-section">
            <div class="section-header">
                <h2 class="section-title">📋 今日任务</h2>
                <button class="refresh-btn" onclick="location.reload()">刷新状态</button>
            </div>
            <div class="task-list">
                {% for task in tasks %}
                <div class="task-item">
                    <div class="task-agent">{{ task.agent_emoji }}</div>
                    <div class="task-content">
                        <div class="task-title">{{ task.title }}</div>
                        <div class="task-meta">
                            <span>{{ task.agent_name }}</span>
                            <span class="task-model">🤖 {{ task.model }}</span>
                            <span>🕐 {{ task.started_at[11:16] if task.started_at else 'N/A' }}</span>
                        </div>
                    </div>
                    <span class="task-priority {{ task.priority }}">{{ task.priority }}</span>
                    <span class="task-status-badge {{ task.status }}">{{ task.status }}</span>
                </div>
                {% endfor %}
            </div>
        </section>
    </main>

    <!-- 详情弹窗 -->
    <div class="modal-overlay" id="agentModal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">×</button>
            <div class="modal-header">
                <div class="modal-avatar" id="modalAvatar">🤖</div>
                <div class="modal-title">
                    <h2 id="modalName">Agent Name</h2>
                    <p id="modalRole">Role Description</p>
                </div>
            </div>
            <div class="config-section">
                <h3>⚙️ 配置信息</h3>
                <div class="config-item">
                    <span class="config-label">Agent ID</span>
                    <span class="config-value" id="modalAgentId">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">所属层级</span>
                    <span class="config-value" id="modalLayer">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">使用模型</span>
                    <span class="config-value" id="modalModel">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">当前状态</span>
                    <span class="config-value" id="modalStatus">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">运行时长</span>
                    <span class="config-value" id="modalDuration">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">最后活跃</span>
                    <span class="config-value" id="modalLastActive">-</span>
                </div>
            </div>
            <div class="config-section">
                <h3>📋 当前任务</h3>
                <div id="modalTask">暂无任务</div>
            </div>
            <div class="config-section">
                <h3>📜 历史记录</h3>
                <div class="history-list" id="modalHistory">
                    <div class="history-item">暂无历史记录</div>
                </div>
            </div>
        </div>
    </div>

    <!-- 页脚 -->
    <footer class="footer">
        <p>🧠 Q 脑 (Q-Brain) 量化交易系统 · 由 小七 协助 十一郎 共同打造</p>
        <p style="margin-top: 8px; opacity: 0.6;">最后更新：{{ now }}</p>
        <p style="margin-top: 4px; opacity: 0.5; font-size: 11px;">支持 OpenClaw Subagents 实时同步</p>
    </footer>

    <script>
        // 自动刷新页面 (每 30 秒)
        setTimeout(() => location.reload(), 30000);
        
        // 同步 OpenClaw 状态
        function syncAgents() {
            const btn = document.getElementById('syncBtn');
            btn.classList.add('syncing');
            btn.innerHTML = '<span class="spinner">🔄</span> 同步中...';
            
            fetch('/api/sync')
                .then(response => response.json())
                .then(data => {
                    btn.classList.remove('syncing');
                    btn.innerHTML = '<span>✅</span> 同步完成';
                    setTimeout(() => {
                        btn.innerHTML = '<span>🔄</span> 同步 OpenClaw 状态';
                        location.reload();
                    }, 1000);
                })
                .catch(error => {
                    btn.classList.remove('syncing');
                    btn.innerHTML = '<span>❌</span> 同步失败';
                    console.error('同步失败:', error);
                });
        }
        
        // 显示 Agent 详情
        function showAgentDetails(agentId) {
            fetch(`/api/agent/${agentId}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('modalAvatar').textContent = data.emoji || '🤖';
                    document.getElementById('modalName').textContent = data.name || agentId;
                    document.getElementById('modalRole').textContent = data.description || '-';
                    document.getElementById('modalAgentId').textContent = data.agent_id || '-';
                    document.getElementById('modalLayer').textContent = data.layer || '-';
                    document.getElementById('modalModel').textContent = data.model || '-';
                    document.getElementById('modalStatus').textContent = data.status || '-';
                    document.getElementById('modalDuration').textContent = data.running_duration || '-';
                    document.getElementById('modalLastActive').textContent = data.last_active ? data.last_active.replace('T', ' ').substring(0, 16) : '-';
                    document.getElementById('modalTask').textContent = data.current_task || '暂无任务';
                    
                    // 加载历史任务
                    loadAgentHistory(agentId);
                    
                    document.getElementById('agentModal').classList.add('active');
                })
                .catch(error => {
                    console.error('获取 Agent 详情失败:', error);
                });
        }
        
        // 加载 Agent 历史任务
        function loadAgentHistory(agentId) {
            fetch(`/api/tasks?agent_id=${agentId}&limit=5`)
                .then(response => response.json())
                .then(tasks => {
                    const historyList = document.getElementById('modalHistory');
                    if (tasks && tasks.length > 0) {
                        historyList.innerHTML = tasks.map(task => `
                            <div class="history-item">
                                <div class="history-time">${task.started_at ? task.started_at.substring(0, 16).replace('T', ' ') : '-'}</div>
                                <div>${task.title}</div>
                                <div style="color: ${task.status === 'completed' ? '#10b981' : task.status === 'running' ? '#10b981' : '#ef4444'}; font-size: 11px; margin-top: 4px;">
                                    ${task.status} ${task.quality_score ? `· 质量分: ${task.quality_score}` : ''}
                                </div>
                            </div>
                        `).join('');
                    } else {
                        historyList.innerHTML = '<div class="history-item">暂无历史记录</div>';
                    }
                })
                .catch(error => {
                    console.error('获取历史任务失败:', error);
                });
        }
        
        // 关闭弹窗
        function closeModal() {
            document.getElementById('agentModal').classList.remove('active');
        }
        
        // 点击弹窗外部关闭
        document.getElementById('agentModal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """主页面"""
    # 获取统计数据
    stats = get_dashboard_stats()
    
    # 按层级分组 Agent
    agents = get_all_agents()
    agents_by_layer = {}
    for agent in agents:
        layer = agent['layer']
        if layer not in agents_by_layer:
            agents_by_layer[layer] = []
        agents_by_layer[layer].append(agent)
    
    # 获取今日任务
    tasks = get_agent_tasks(limit=20)
    
    return render_template_string(
        HTML_TEMPLATE,
        stats=stats,
        layers=stats.get('layer_distribution', {}),
        agents_by_layer=agents_by_layer,
        tasks=tasks,
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/api/stats')
def api_stats():
    """API: 统计数据"""
    return jsonify(get_dashboard_stats())

@app.route('/api/agents')
def api_agents():
    """API: 所有 Agent"""
    return jsonify(get_all_agents())

@app.route('/api/agent/<agent_id>')
def api_agent_detail(agent_id):
    """API: 单个 Agent 详情"""
    agents = get_all_agents()
    for agent in agents:
        if agent['agent_id'] == agent_id:
            return jsonify(agent)
    return jsonify({'error': 'Agent not found'}), 404

@app.route('/api/tasks')
def api_tasks():
    """API: 任务列表"""
    agent_id = request.args.get('agent_id')
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    return jsonify(get_agent_tasks(agent_id=agent_id, status=status, limit=limit))

@app.route('/api/sync')
def api_sync():
    """API: 同步 OpenClaw 状态"""
    try:
        sync_openclaw_agents()
        return jsonify({'status': 'success', 'message': '同步完成'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    print("🚀 启动 Q 脑 Agent 管理 Dashboard (端口 5007)")
    print("🤖 访问地址：http://localhost:5007")
    print("📡 支持 OpenClaw Subagents 实时同步")
    app.run(host='0.0.0.0', port=5007, debug=False)
