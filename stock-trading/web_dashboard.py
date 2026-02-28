"""
模拟交易可视化网页服务 - 现代化深色主题
Flask + Chart.js + 玻璃拟态设计
"""
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import sqlite3
import os
import json

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'trading.db')
INITIAL_CAPITAL = 100000.0

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_positions():
    conn = get_db()
    rows = conn.execute('SELECT * FROM positions ORDER BY symbol').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_trades(limit=50):
    conn = get_db()
    rows = conn.execute('SELECT * FROM trades ORDER BY trade_date DESC, id DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_snapshots(limit=30):
    conn = get_db()
    rows = conn.execute('SELECT * FROM daily_snapshots ORDER BY snapshot_date DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) as c FROM trades').fetchone()['c']
    buys = conn.execute("SELECT COUNT(*) as c FROM trades WHERE trade_type='buy'").fetchone()['c']
    sells = conn.execute("SELECT COUNT(*) as c FROM trades WHERE trade_type='sell'").fetchone()['c']
    win = conn.execute("SELECT SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) as w FROM trades WHERE trade_type='sell'").fetchone()['w'] or 0
    sell_total = sells or 1
    conn.close()
    return {'total': total, 'buys': buys, 'sells': sells, 'win_rate': round(win/sell_total*100, 1)}

HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quant Trading Pro | 模拟交易监控</title>
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
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 20px;
            font-size: 13px;
            color: var(--accent-green);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
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
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }
        
        .stat-value {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .stat-change {
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .positive { color: var(--accent-green); }
        .negative { color: var(--accent-red); }
        
        /* Charts Section */
        .charts-section {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 32px;
        }
        
        .chart-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
        }
        
        .chart-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .chart-container { position: relative; height: 300px; }
        
        /* Tables */
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
        }
        
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .badge-buy {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
        }
        
        .badge-sell {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(139, 92, 246, 0.3);
        }
        
        @media (max-width: 1024px) {
            .charts-section { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <h1>Quant Trading Pro</h1>
                <p>模拟交易监控系统 | 策略: optimized_v2 | 仓位: 30%</p>
            </div>
            <div style="display: flex; gap: 12px; align-items: center;">
                <span style="color: var(--text-secondary); font-size: 13px;">更新: {{ last_update }}</span>
                <button class="refresh-btn" onclick="location.reload()">🔄 刷新</button>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">总资产</div>
                <div class="stat-value">${{ "{:,.2f}".format(stats['total_value']) }}</div>
                <div class="stat-change {{ 'positive' if stats['total_return'] >= 0 else 'negative' }}">
                    {{ "↑" if stats['total_return'] >= 0 else "↓" }} {{ "{:.2f}".format(stats['total_return']) }}% (${{ "{:,.2f}".format(stats['total_return_value']) }})
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-label">可用现金</div>
                <div class="stat-value">${{ "{:,.2f}".format(stats['cash']) }}</div>
                <div class="stat-change" style="color: var(--text-secondary);">{{ "{:.1f}".format(stats['cash_pct']) }}% 仓位</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">持仓市值</div>
                <div class="stat-value">${{ "{:,.2f}".format(stats['position_value']) }}</div>
                <div class="stat-change" style="color: var(--text-secondary);">{{ stats['positions_count'] }} 只股票</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">胜率 / 交易数</div>
                <div class="stat-value">{{ stats['win_rate'] }}%</div>
                <div class="stat-change" style="color: var(--text-secondary);">{{ stats['total_trades'] }} 笔交易 ({{ stats['buy_count'] }}买/{{ stats['sell_count'] }}卖)</div>
            </div>
        </div>
        
        <div class="charts-section">
            <div class="chart-card">
                <div class="chart-title">📈 资产走势</div>
                <div class="chart-container">
                    <canvas id="valueChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <div class="chart-title">📊 收益分布</div>
                <div class="chart-container">
                    <canvas id="pnlChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="section-title">📦 当前持仓</div>
        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th>股票代码</th>
                        <th>股数</th>
                        <th>成本价</th>
                        <th>当前价</th>
                        <th>市值</th>
                        <th>盈亏</th>
                        <th>盈亏率</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in positions %}
                    <tr>
                        <td><strong>{{ p['symbol'] }}</strong></td>
                        <td>{{ p['shares'] }}</td>
                        <td>${{ "{:.2f}".format(p['average_cost']) }}</td>
                        <td>${{ "{:.2f}".format(p['current_price']) }}</td>
                        <td>${{ "{:,.2f}".format(p['market_value']) }}</td>
                        <td class="{{ 'positive' if p['unrealized_pnl'] >= 0 else 'negative' }}">${{ "{:,.2f}".format(p['unrealized_pnl']) }}</td>
                        <td class="{{ 'positive' if p['unrealized_pnl_pct'] >= 0 else 'negative' }}">{{ "{:.2f}".format(p['unrealized_pnl_pct']) }}%</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 40px;">暂无持仓</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="section-title">📝 最近交易</div>
        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>股票</th>
                        <th>类型</th>
                        <th>价格</th>
                        <th>股数</th>
                        <th>金额</th>
                        <th>盈亏</th>
                    </tr>
                </thead>
                <tbody>
                    {% for t in trades %}
                    <tr>
                        <td>{{ t['trade_date'] }}</td>
                        <td><strong>{{ t['symbol'] }}</strong></td>
                        <td><span class="badge badge-{{ t['trade_type'] }}">{{ '买入' if t['trade_type'] == 'buy' else '卖出' }}</span></td>
                        <td>${{ "{:.2f}".format(t['price']) }}</td>
                        <td>{{ t['shares'] }}</td>
                        <td>${{ "{:,.2f}".format(t['value']) }}</td>
                        <td class="{{ 'positive' if t['pnl'] >= 0 else 'negative' }}">${{ "{:,.2f}".format(t['pnl']) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 40px;">暂无交易记录</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        const snapshots = {{ snapshots_json | safe }};
        const dates = snapshots.map(s => s.snapshot_date);
        const values = snapshots.map(s => s.total_value);
        const returns = snapshots.map(s => s.daily_return);
        
        // 资产走势图
        new Chart(document.getElementById('valueChart'), {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: '总资产',
                    data: values,
                    borderColor: '#06b6d4',
                    backgroundColor: 'rgba(6, 182, 212, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(75, 85, 99, 0.2)' }, ticks: { color: '#9ca3af' } },
                    y: { grid: { color: 'rgba(75, 85, 99, 0.2)' }, ticks: { color: '#9ca3af' } }
                }
            }
        });
        
        // 收益分布图
        new Chart(document.getElementById('pnlChart'), {
            type: 'doughnut',
            data: {
                labels: ['盈利天数', '亏损天数'],
                datasets: [{
                    data: [
                        returns.filter(r => r > 0).length,
                        returns.filter(r => r < 0).length
                    ],
                    backgroundColor: ['#10b981', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#9ca3af' } }
                }
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    positions = get_positions()
    trades = get_trades(20)
    snapshots = get_snapshots(30)
    stats_data = get_stats()
    
    latest = snapshots[0] if snapshots else None
    total_value = latest['total_value'] if latest else INITIAL_CAPITAL
    total_return_val = latest['total_return'] if latest else 0
    
    stats = {
        'total_value': total_value,
        'total_return': latest['total_return_pct'] if latest else 0,
        'total_return_value': total_return_val,
        'cash': latest['cash'] if latest else INITIAL_CAPITAL,
        'cash_pct': (latest['cash'] / total_value * 100) if latest and total_value > 0 else 100,
        'position_value': latest['position_value'] if latest else 0,
        'positions_count': len(positions),
        'win_rate': stats_data.get('win_rate', 0),
        'total_trades': stats_data.get('total', 0),
        'buy_count': stats_data.get('buys', 0),
        'sell_count': stats_data.get('sells', 0)
    }
    
    return render_template_string(HTML, 
        positions=positions, 
        trades=trades, 
        snapshots=json.dumps(snapshots),
        stats=stats,
        last_update=datetime.now().strftime('%H:%M:%S')
    )

if __name__ == '__main__':
    print("🚀 启动模拟交易监控 (端口 5001)")
    app.run(host='0.0.0.0', port=5001, debug=False)
