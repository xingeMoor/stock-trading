"""
模拟交易可视化网页服务 - 简化版
Flask + Chart.js 展示交易记录、持仓、绩效等
"""
from flask import Flask, render_template_string, jsonify
from datetime import datetime
import sqlite3
import os
import json

app = Flask(__name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'trading.db')
INITIAL_CAPITAL = 100000.0  # 10 万美元


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_trades(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM trades ORDER BY trade_date DESC, id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_positions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM positions ORDER BY symbol')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_snapshots(limit=30):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM daily_snapshots ORDER BY snapshot_date DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_statistics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM trades')
    total_trades = cursor.fetchone()['count']
    
    cursor.execute('SELECT trade_type, COUNT(*) as count FROM trades GROUP BY trade_type')
    type_counts = {row['trade_type']: row['count'] for row in cursor.fetchall()}
    
    cursor.execute('SELECT AVG(pnl) as avg_pnl, SUM(pnl) as total_pnl FROM trades WHERE trade_type = \'sell\'')
    pnl_stats = cursor.fetchone()
    
    cursor.execute('SELECT SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins, COUNT(*) as total FROM trades WHERE trade_type = \'sell\'')
    win_stats = cursor.fetchone()
    win_rate = win_stats['wins'] / win_stats['total'] * 100 if win_stats['total'] > 0 else 0
    
    conn.close()
    
    return {
        'total_trades': total_trades,
        'buy_count': type_counts.get('buy', 0),
        'sell_count': type_counts.get('sell', 0),
        'avg_pnl': pnl_stats['avg_pnl'] or 0,
        'total_pnl': pnl_stats['total_pnl'] or 0,
        'win_count': win_stats['wins'] or 0,
        'win_rate': round(win_rate, 2)
    }


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>量化交易监控 - 模拟盘</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header h1 { color: #333; font-size: 32px; margin-bottom: 10px; }
        .header .subtitle { color: #666; font-size: 16px; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .stat-card .label { color: #666; font-size: 14px; margin-bottom: 10px; }
        .stat-card .value { font-size: 32px; font-weight: bold; color: #333; }
        .stat-card .value.positive { color: #10b981; }
        .stat-card .value.negative { color: #ef4444; }
        .chart-container, .table-container {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .chart-container h2, .table-container h2 {
            color: #333; font-size: 24px; margin-bottom: 20px;
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #f3f4f6; padding: 15px; text-align: left;
            font-weight: 600; color: #374151;
        }
        td { padding: 15px; border-bottom: 1px solid #e5e7eb; color: #4b5563; }
        tr:hover { background: #f9fafb; }
        .badge {
            display: inline-block; padding: 4px 12px;
            border-radius: 20px; font-size: 12px; font-weight: 600;
        }
        .badge-buy { background: #d1fae5; color: #065f46; }
        .badge-sell { background: #fee2e2; color: #991b1b; }
        .refresh-btn {
            background: #667eea; color: white; border: none;
            padding: 10px 20px; border-radius: 8px; cursor: pointer;
        }
        .refresh-btn:hover { background: #5568d3; }
        .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; }
        @media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 量化交易监控 - 模拟盘</h1>
            <p class="subtitle">初始资金：$100,000 | 策略：optimized_v2 | 仓位：30%</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
            <p style="color:#666;font-size:14px;margin-top:10px;">最后更新：{{ last_update }}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">💰 总资产</div>
                <div class="value">${{ "%.2f"|format(stats.total_value) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">📊 总收益</div>
                <div class="value {{ 'positive' if stats.total_return >= 0 else 'negative' }}">
                    ${{ "%.2f"|format(stats.total_return) }} ({{ "%.2f"|format(stats.total_return_pct) }}%)
                </div>
            </div>
            <div class="stat-card">
                <div class="label">💵 可用现金</div>
                <div class="value">${{ "%.2f"|format(stats.cash) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">📈 持仓市值</div>
                <div class="value">${{ "%.2f"|format(stats.position_value) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">🎯 胜率</div>
                <div class="value">{{ statistics.win_rate }}%</div>
            </div>
            <div class="stat-card">
                <div class="label">📝 总交易</div>
                <div class="value">{{ statistics.total_trades }}</div>
            </div>
        </div>
        
        <div class="grid-2">
            <div class="chart-container">
                <h2>📊 资产变化曲线</h2>
                <canvas id="valueChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>📈 每日收益</h2>
                <canvas id="returnChart"></canvas>
            </div>
        </div>
        
        <div class="table-container">
            <h2>📦 当前持仓</h2>
            <table>
                <thead>
                    <tr><th>股票</th><th>股数</th><th>成本价</th><th>当前价</th><th>市值</th><th>盈亏</th><th>盈亏率</th></tr>
                </thead>
                <tbody>
                    {% for pos in positions %}
                    <tr>
                        <td><strong>{{ pos.symbol }}</strong></td>
                        <td>{{ pos.shares }}</td>
                        <td>${{ "%.2f"|format(pos.average_cost) }}</td>
                        <td>${{ "%.2f"|format(pos.current_price) }}</td>
                        <td>${{ "%.2f"|format(pos.market_value) }}</td>
                        <td class="{{ 'positive' if pos.unrealized_pnl >= 0 else 'negative' }}">
                            ${{ "%.2f"|format(pos.unrealized_pnl) }}
                        </td>
                        <td class="{{ 'positive' if pos.unrealized_pnl_pct >= 0 else 'negative' }}">
                            {{ "%.2f"|format(pos.unrealized_pnl_pct) }}%
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align:center;color:#999;">暂无持仓</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="table-container">
            <h2>📝 最近交易</h2>
            <table>
                <thead>
                    <tr><th>日期</th><th>股票</th><th>类型</th><th>价格</th><th>股数</th><th>金额</th><th>盈亏</th></tr>
                </thead>
                <tbody>
                    {% for trade in trades %}
                    <tr>
                        <td>{{ trade.trade_date }}</td>
                        <td><strong>{{ trade.symbol }}</strong></td>
                        <td>
                            <span class="badge badge-{{ trade.trade_type }}">
                                {{ '买入' if trade.trade_type == 'buy' else '卖出' }}
                            </span>
                        </td>
                        <td>${{ "%.2f"|format(trade.price) }}</td>
                        <td>{{ trade.shares }}</td>
                        <td>${{ "%.2f"|format(trade.value) }}</td>
                        <td class="{{ 'positive' if trade.pnl >= 0 else 'negative' }}">
                            ${{ "%.2f"|format(trade.pnl) }}
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align:center;color:#999;">暂无交易记录</td></tr>
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
        
        // 资产曲线
        new Chart(document.getElementById('valueChart'), {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: '总资产',
                    data: values,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: false } }
            }
        });
        
        // 每日收益
        new Chart(document.getElementById('returnChart'), {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [{
                    label: '每日收益',
                    data: returns,
                    backgroundColor: returns.map(v => v >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)')
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } }
            }
        });
        
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    positions = get_positions()
    trades = get_trades(limit=50)
    snapshots = get_snapshots(limit=30)
    statistics = get_statistics()
    
    latest = snapshots[0] if snapshots else None
    stats = {
        'total_value': latest['total_value'] if latest else INITIAL_CAPITAL,
        'total_return': latest['total_return'] if latest else 0,
        'total_return_pct': latest['total_return_pct'] if latest else 0,
        'cash': latest['cash'] if latest else INITIAL_CAPITAL,
        'position_value': latest['position_value'] if latest else 0
    }
    
    snapshots_reversed = list(reversed(snapshots))
    
    return render_template_string(
        HTML_TEMPLATE,
        positions=positions,
        trades=trades,
        snapshots_json=json.dumps(snapshots_reversed),
        statistics=statistics,
        stats=stats,
        last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


@app.route('/api/summary')
def api_summary():
    snapshots = get_snapshots(limit=1)
    statistics = get_statistics()
    latest = snapshots[0] if snapshots else None
    return jsonify({
        'total_value': latest['total_value'] if latest else INITIAL_CAPITAL,
        'total_return': latest['total_return'] if latest else 0,
        'total_return_pct': latest['total_return_pct'] if latest else 0,
        'cash': latest['cash'] if latest else INITIAL_CAPITAL,
        'position_value': latest['position_value'] if latest else 0,
        'statistics': statistics,
        'last_update': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 启动量化交易监控服务")
    print("="*60)
    print(f"\n📊 访问地址：http://localhost:5001")
    print(f"💾 数据库：{DB_PATH}")
    print(f"💰 初始资金：${INITIAL_CAPITAL:,.2f}")
    print("\n按 Ctrl+C 停止服务\n")
    app.run(host='0.0.0.0', port=5001, debug=False)
