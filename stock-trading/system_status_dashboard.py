"""
系统状态监控Dashboard - 现代化深色主题
Flask + Chart.js + 玻璃拟态设计
端口: 5006
"""
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import sqlite3
import os
import json
import random

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'trading.db')

# ============ 模拟数据生成器 ============
def generate_mock_tools():
    """生成模拟工具状态数据"""
    tools = [
        {"name": "Alpha Vantage", "type": "美股", "status": "normal", "response_time": 245},
        {"name": "Yahoo Finance", "type": "美股", "status": "normal", "response_time": 189},
        {"name": "Tushare Pro", "type": "A股", "status": "normal", "response_time": 312},
        {"name": "AKShare", "type": "A股", "status": "warning", "response_time": 1250},
        {"name": "Polygon.io", "type": "美股", "status": "normal", "response_time": 156},
        {"name": "新浪财经", "type": "A股", "status": "normal", "response_time": 278},
        {"name": "东方财富", "type": "A股", "status": "error", "response_time": 0},
        {"name": "Finnhub", "type": "美股", "status": "normal", "response_time": 203},
    ]
    
    # 随机更新一些状态
    for tool in tools:
        tool['last_check'] = (datetime.now() - timedelta(seconds=random.randint(10, 300))).strftime('%H:%M:%S')
        if tool['status'] == 'error':
            tool['response_time'] = 0
    
    return tools

def generate_feishu_status():
    """生成飞书状态数据"""
    return {
        "webhook": {
            "status": "normal",
            "url": "https://open.feishu.cn/open-apis/bot/v2/hook/...",
            "last_test": (datetime.now() - timedelta(minutes=5)).strftime('%H:%M:%S'),
            "success_rate": 98.5
        },
        "app": {
            "status": "normal",
            "app_name": "StockTrading Bot",
            "app_id": "cli_xxxxxxxxxxxx",
            "token_expiry": (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
            "permissions": ["im:message:send", "im:message:read"]
        },
        "recent_messages": [
            {"time": "09:30:15", "type": "买入信号", "content": "AAPL 触发买入 @ $178.50", "status": "sent"},
            {"time": "09:28:42", "type": "卖出提醒", "content": "TSLA 止盈卖出 @ $245.30", "status": "sent"},
            {"time": "09:15:00", "type": "系统通知", "content": "每日市场扫描完成", "status": "sent"},
            {"time": "08:45:22", "type": "错误告警", "content": "东方财富API连接超时", "status": "failed"},
            {"time": "08:30:00", "type": "系统启动", "content": "交易系统初始化完成", "status": "sent"},
        ]
    }

def generate_tool_history(tool_name):
    """生成工具历史响应时间数据"""
    hours = 24
    data = []
    base_time = datetime.now() - timedelta(hours=hours)
    
    for i in range(hours):
        timestamp = base_time + timedelta(hours=i)
        # 模拟响应时间波动
        base_response = random.choice([150, 200, 250, 300])
        response_time = base_response + random.randint(-50, 100)
        status = "normal" if response_time < 500 else "warning" if response_time < 1000 else "error"
        
        data.append({
            "time": timestamp.strftime('%H:%M'),
            "response_time": max(50, response_time),
            "status": status
        })
    
    return data

# ============ 路由 ============

@app.route('/')
def index():
    """主页面"""
    tools = generate_mock_tools()
    feishu = generate_feishu_status()
    
    # 统计数据
    total_tools = len(tools)
    normal_tools = sum(1 for t in tools if t['status'] == 'normal')
    error_tools = sum(1 for t in tools if t['status'] == 'error')
    warning_tools = sum(1 for t in tools if t['status'] == 'warning')
    
    stats = {
        "total": total_tools,
        "normal": normal_tools,
        "warning": warning_tools,
        "error": error_tools,
        "feishu_status": feishu['webhook']['status'],
        "last_check": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return render_template_string(HTML, 
        tools=tools,
        feishu=feishu,
        stats=stats
    )

@app.route('/api/status')
def api_status():
    """API: 获取当前状态"""
    tools = generate_mock_tools()
    feishu = generate_feishu_status()
    
    total_tools = len(tools)
    normal_tools = sum(1 for t in tools if t['status'] == 'normal')
    error_tools = sum(1 for t in tools if t['status'] == 'error')
    warning_tools = sum(1 for t in tools if t['status'] == 'warning')
    
    return jsonify({
        "tools": tools,
        "feishu": feishu,
        "stats": {
            "total": total_tools,
            "normal": normal_tools,
            "warning": warning_tools,
            "error": error_tools,
            "feishu_status": feishu['webhook']['status'],
            "last_check": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    })

@app.route('/api/tool-history/<tool_name>')
def api_tool_history(tool_name):
    """API: 获取工具历史数据"""
    history = generate_tool_history(tool_name)
    return jsonify({
        "tool_name": tool_name,
        "history": history
    })

# ============ HTML模板 ============

HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Status Monitor | 系统状态监控</title>
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
        
        .container { max-width: 1400px; margin: 0 auto; padding: 24px; }
        
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
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }
        
        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
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
        
        .stat-card.normal::before { background: linear-gradient(90deg, var(--accent-green), #34d399); }
        .stat-card.warning::before { background: linear-gradient(90deg, var(--accent-yellow), #fbbf24); }
        .stat-card.error::before { background: linear-gradient(90deg, var(--accent-red), #f87171); }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .stat-value {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .stat-value.small {
            font-size: 24px;
        }
        
        .stat-change {
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .positive { color: var(--accent-green); }
        .negative { color: var(--accent-red); }
        .warning { color: var(--accent-yellow); }
        
        /* Feishu Section */
        .feishu-section {
            display: grid;
            grid-template-columns: 1fr 1fr 1.5fr;
            gap: 20px;
            margin-bottom: 32px;
        }
        
        @media (max-width: 1200px) {
            .feishu-section { grid-template-columns: 1fr 1fr; }
        }
        
        @media (max-width: 768px) {
            .feishu-section { grid-template-columns: 1fr; }
        }
        
        .feishu-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
        }
        
        .feishu-card h3 {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        
        .status-row:last-child { border-bottom: none; }
        
        .status-label { color: var(--text-secondary); font-size: 14px; }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-badge.normal {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
        }
        
        .status-badge.warning {
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
        }
        
        .status-badge.normal .status-dot { background: var(--accent-green); }
        .status-badge.warning .status-dot { background: var(--accent-yellow); }
        .status-badge.error .status-dot { background: var(--accent-red); }
        
        /* Message List */
        .message-list {
            max-height: 280px;
            overflow-y: auto;
        }
        
        .message-item {
            display: flex;
            gap: 12px;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 8px;
            background: rgba(255, 255, 255, 0.02);
            transition: background 0.2s;
        }
        
        .message-item:hover { background: rgba(255, 255, 255, 0.05); }
        
        .message-time {
            font-size: 12px;
            color: var(--text-secondary);
            min-width: 60px;
        }
        
        .message-content {
            flex: 1;
        }
        
        .message-type {
            font-size: 12px;
            font-weight: 500;
            margin-bottom: 4px;
        }
        
        .message-text {
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        .message-status {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
        }
        
        .message-status.sent {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
        }
        
        .message-status.failed {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
        }
        
        /* Tools Table */
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .table-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        th {
            text-align: left;
            padding: 16px 12px;
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
        }
        
        td {
            padding: 16px 12px;
            border-bottom: 1px solid var(--border);
            color: var(--text-primary);
        }
        
        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
            cursor: pointer;
        }
        
        .tool-name {
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .tool-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        
        .tool-icon.us { background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); }
        .tool-icon.cn { background: rgba(139, 92, 246, 0.15); color: var(--accent-purple); }
        
        .response-time {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .response-bar {
            width: 60px;
            height: 4px;
            background: rgba(75, 85, 99, 0.3);
            border-radius: 2px;
            overflow: hidden;
        }
        
        .response-bar-fill {
            height: 100%;
            border-radius: 2px;
            transition: width 0.3s;
        }
        
        .response-bar-fill.fast { background: var(--accent-green); }
        .response-bar-fill.medium { background: var(--accent-yellow); }
        .response-bar-fill.slow { background: var(--accent-red); }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(5px);
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
            max-width: 800px;
            max-height: 80vh;
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
        
        .chart-container {
            position: relative;
            height: 300px;
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
                <h1>🔧 System Status Monitor</h1>
                <p>系统状态监控 Dashboard | 实时监测工具与飞书服务状态</p>
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
                <div class="stat-label">📊 总工具数</div>
                <div class="stat-value" id="stat-total">{{ stats.total }}</div>
                <div class="stat-change" style="color: var(--text-secondary);">监控中的API服务</div>
            </div>
            <div class="stat-card normal">
                <div class="stat-label">✅ 正常运行</div>
                <div class="stat-value positive" id="stat-normal">{{ stats.normal }}</div>
                <div class="stat-change positive">
                    {{ "%.1f"|format(stats.normal / stats.total * 100) }}% 可用率
                </div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">⚠️ 警告状态</div>
                <div class="stat-value warning" id="stat-warning">{{ stats.warning }}</div>
                <div class="stat-change warning">需要关注</div>
            </div>
            <div class="stat-card error">
                <div class="stat-label">❌ 异常故障</div>
                <div class="stat-value negative" id="stat-error">{{ stats.error }}</div>
                <div class="stat-change negative">请立即检查</div>
            </div>
            <div class="stat-card {{ 'normal' if stats.feishu_status == 'normal' else 'error' }}">
                <div class="stat-label">📱 飞书状态</div>
                <div class="stat-value small {{ 'positive' if stats.feishu_status == 'normal' else 'negative' }}" id="stat-feishu">
                    {{ '正常' if stats.feishu_status == 'normal' else '异常' }}
                </div>
                <div class="stat-change" style="color: var(--text-secondary);">Webhook & App</div>
            </div>
        </div>
        
        <!-- Feishu Section -->
        <div class="section-title">📱 飞书服务状态</div>
        <div class="feishu-section">
            <div class="feishu-card">
                <h3>🔗 Webhook 状态</h3>
                <div class="status-row">
                    <span class="status-label">连接状态</span>
                    <span class="status-badge {{ feishu.webhook.status }}">
                        <span class="status-dot"></span>
                        {{ '正常' if feishu.webhook.status == 'normal' else '异常' }}
                    </span>
                </div>
                <div class="status-row">
                    <span class="status-label">成功率</span>
                    <span style="font-weight: 600; color: var(--accent-green);">{{ feishu.webhook.success_rate }}%</span>
                </div>
                <div class="status-row">
                    <span class="status-label">最后测试</span>
                    <span style="color: var(--text-secondary);">{{ feishu.webhook.last_test }}</span>
                </div>
            </div>
            
            <div class="feishu-card">
                <h3>🔐 自建应用状态</h3>
                <div class="status-row">
                    <span class="status-label">应用状态</span>
                    <span class="status-badge {{ feishu.app.status }}">
                        <span class="status-dot"></span>
                        {{ '正常' if feishu.app.status == 'normal' else '异常' }}
                    </span>
                </div>
                <div class="status-row">
                    <span class="status-label">Token过期</span>
                    <span style="color: var(--text-secondary);">{{ feishu.app.token_expiry }}</span>
                </div>
                <div class="status-row">
                    <span class="status-label">权限数量</span>
                    <span style="font-weight: 600;">{{ feishu.app.permissions|length }} 项</span>
                </div>
            </div>
            
            <div class="feishu-card">
                <h3>💬 最近消息记录</h3>
                <div class="message-list">
                    {% for msg in feishu.recent_messages %}
                    <div class="message-item">
                        <div class="message-time">{{ msg.time }}</div>
                        <div class="message-content">
                            <div class="message-type" style="color: {{ '#10b981' if msg.type == '买入信号' else '#ef4444' if msg.type == '卖出提醒' else '#f59e0b' if msg.type == '错误告警' else '#06b6d4' }};">
                                {{ msg.type }}
                            </div>
                            <div class="message-text">{{ msg.content }}</div>
                        </div>
                        <div class="message-status {{ msg.status }}">{{ '已发送' if msg.status == 'sent' else '失败' }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <!-- Tools Table -->
        <div class="section-title">🛠️ 工具状态监控</div>
        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th>工具名称</th>
                        <th>类型</th>
                        <th>状态</th>
                        <th>响应时间</th>
                        <th>最后检查</th>
                    </tr>
                </thead>
                <tbody id="tools-table-body">
                    {% for tool in tools %}
                    <tr onclick="showToolHistory('{{ tool.name }}')">
                        <td>
                            <div class="tool-name">
                                <div class="tool-icon {{ 'us' if tool.type == '美股' else 'cn' }}">
                                    {{ '🇺🇸' if tool.type == '美股' else '🇨🇳' }}
                                </div>
                                {{ tool.name }}
                            </div>
                        </td>
                        <td>{{ tool.type }}</td>
                        <td>
                            <span class="status-badge {{ tool.status }}">
                                <span class="status-dot"></span>
                                {{ '正常' if tool.status == 'normal' else '警告' if tool.status == 'warning' else '异常' }}
                            </span>
                        </td>
                        <td>
                            <div class="response-time">
                                <span>{{ tool.response_time }}ms</span>
                                <div class="response-bar">
                                    <div class="response-bar-fill {{ 'fast' if tool.response_time < 300 else 'medium' if tool.response_time < 800 else 'slow' }}" 
                                         style="width: {{ min(tool.response_time / 15, 100) }}%;"></div>
                                </div>
                            </div>
                        </td>
                        <td style="color: var(--text-secondary);">{{ tool.last_check }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="last-update">
                <span>⏱️ 最后更新:</span>
                <span id="last-update-time">{{ stats.last_check }}</span>
            </div>
        </div>
    </div>
    
    <!-- History Modal -->
    <div class="modal-overlay" id="historyModal" onclick="closeModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title" id="modalTitle">工具历史趋势</div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="chart-container">
                <canvas id="historyChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        let historyChart = null;
        let autoRefreshInterval = null;
        
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            startAutoRefresh();
        });
        
        // 自动刷新
        function startAutoRefresh() {
            autoRefreshInterval = setInterval(() => {
                fetchStatus();
            }, 30000); // 30秒
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
            document.getElementById('stat-total').textContent = data.stats.total;
            document.getElementById('stat-normal').textContent = data.stats.normal;
            document.getElementById('stat-warning').textContent = data.stats.warning;
            document.getElementById('stat-error').textContent = data.stats.error;
            
            const feishuEl = document.getElementById('stat-feishu');
            feishuEl.textContent = data.stats.feishu_status === 'normal' ? '正常' : '异常';
            feishuEl.className = 'stat-value small ' + (data.stats.feishu_status === 'normal' ? 'positive' : 'negative');
            
            // 更新时间
            document.getElementById('last-update-time').textContent = data.stats.last_check;
            
            // 更新工具表格
            updateToolsTable(data.tools);
        }
        
        // 更新工具表格
        function updateToolsTable(tools) {
            const tbody = document.getElementById('tools-table-body');
            tbody.innerHTML = tools.map(tool => `
                <tr onclick="showToolHistory('${tool.name}')">
                    <td>
                        <div class="tool-name">
                            <div class="tool-icon ${tool.type === '美股' ? 'us' : 'cn'}">
                                ${tool.type === '美股' ?? '🇺🇸' : '🇨🇳'}
                            </div>
                            ${tool.name}
                        </div>
                    </td>
                    <td>${tool.type}</td>
                    <td>
                        <span class="status-badge ${tool.status}">
                            <span class="status-dot"></span>
                            ${tool.status === 'normal' ? '正常' : tool.status === 'warning' ? '警告' : '异常'}
                        </span>
                    </td>
                    <td>
                        <div class="response-time">
                            <span>${tool.response_time}ms</span>
                            <div class="response-bar">
                                <div class="response-bar-fill ${tool.response_time < 300 ? 'fast' : tool.response_time < 800 ? 'medium' : 'slow'}" 
                                     style="width: ${Math.min(tool.response_time / 15, 100)}%;"></div>
                            </div>
                        </div>
                    </td>
                    <td style="color: var(--text-secondary);">${tool.last_check}</td>
                </tr>
            `).join('');
        }
        
        // 显示工具历史
        async function showToolHistory(toolName) {
            const modal = document.getElementById('historyModal');
            const title = document.getElementById('modalTitle');
            title.textContent = `${toolName} - 24小时响应时间趋势`;
            
            modal.classList.add('active');
            
            try {
                const response = await fetch(`/api/tool-history/${encodeURIComponent(toolName)}`);
                const data = await response.json();
                renderHistoryChart(data.history);
            } catch (error) {
                console.error('Failed to fetch history:', error);
            }
        }
        
        // 关闭模态框
        function closeModal(event) {
            if (!event || event.target.id === 'historyModal') {
                document.getElementById('historyModal').classList.remove('active');
            }
        }
        
        // 渲染历史图表
        function renderHistoryChart(history) {
            const ctx = document.getElementById('historyChart').getContext('2d');
            
            if (historyChart) {
                historyChart.destroy();
            }
            
            const labels = history.map(h => h.time);
            const data = history.map(h => h.response_time);
            const colors = history.map(h => {
                if (h.status === 'normal') return '#10b981';
                if (h.status === 'warning') return '#f59e0b';
                return '#ef4444';
            });
            
            historyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '响应时间 (ms)',
                        data: data,
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6, 182, 212, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: colors,
                        pointBorderColor: colors,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(75, 85, 99, 0.2)' },
                            ticks: { color: '#9ca3af' }
                        },
                        y: {
                            grid: { color: 'rgba(75, 85, 99, 0.2)' },
                            ticks: { color: '#9ca3af' },
                            beginAtZero: true
                        }
                    }
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
    print("🚀 启动系统状态监控Dashboard (端口 5006)")
    print("📊 访问地址: http://localhost:5006")
    app.run(host='0.0.0.0', port=5006, debug=False)
