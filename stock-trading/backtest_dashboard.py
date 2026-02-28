"""
回测结果可视化网页服务 - 现代化深色主题
"""
from flask import Flask, render_template_string, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)
BACKTEST_DIR = os.path.join(os.path.dirname(__file__), 'data', 'backtest_results')

def load_results(limit=200):
    results = []
    if not os.path.exists(BACKTEST_DIR):
        return results
    for f in os.listdir(BACKTEST_DIR):
        if f.endswith('.json') and not f.startswith('summary_'):
            try:
                with open(os.path.join(BACKTEST_DIR, f)) as fp:
                    data = json.load(fp)
                    if 'symbol' in data and 'total_return' in data:
                        results.append(data)
            except:
                pass
    results.sort(key=lambda x: x.get('end_date', ''), reverse=True)
    return results[:limit]

def calc_stats(results):
    if not results:
        return {'count': 0, 'avg_return': 0, 'avg_sharpe': 0, 'win_rate': 0}
    returns = [r['total_return'] for r in results]
    sharpes = [r.get('sharpe_ratio', 0) for r in results]
    wins = sum(1 for r in returns if r > 0)
    return {
        'count': len(results),
        'avg_return': round(sum(returns)/len(returns), 2),
        'avg_sharpe': round(sum(sharpes)/len(sharpes), 2) if sharpes else 0,
        'win_rate': round(wins/len(returns)*100, 1),
        'best': max(results, key=lambda x: x['total_return']) if results else None,
        'worst': min(results, key=lambda x: x['total_return']) if results else None
    }

HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Analytics | 回测分析</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --accent-orange: #f97316;
            --accent-blue: #3b82f6;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border: rgba(148, 163, 184, 0.2);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(249, 115, 22, 0.1) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(59, 130, 246, 0.1) 0%, transparent 40%);
        }
        
        .container { max-width: 1600px; margin: 0 auto; padding: 24px; }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }
        
        .header h1 {
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-orange), var(--accent-blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header p { color: var(--text-secondary); margin-top: 4px; }
        
        .stats-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        
        .stat-box {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: all 0.3s;
        }
        
        .stat-box:hover {
            transform: translateY(-2px);
            border-color: var(--accent-orange);
            box-shadow: 0 10px 30px rgba(249, 115, 22, 0.1);
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 4px;
        }
        
        .stat-label {
            font-size: 13px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }
        
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
        }
        
        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .chart-wrapper { height: 280px; }
        
        .results-table {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }
        
        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
        }
        
        .search-input {
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 16px;
            color: var(--text-primary);
            width: 240px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        th, td {
            padding: 16px 20px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        
        th {
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        tr:hover { background: rgba(255,255,255,0.02); }
        
        .return-positive { color: var(--accent-green); font-weight: 600; }
        .return-negative { color: var(--accent-red); font-weight: 600; }
        
        .grade {
            display: inline-flex;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .grade-a { background: rgba(34, 197, 94, 0.15); color: var(--accent-green); }
        .grade-b { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); }
        .grade-c { background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }
        
        @media (max-width: 1024px) {
            .main-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Backtest Analytics</h1>
                <p>回测周期: 2024-01-01 至 2026-02-28 | 策略: optimized_v2</p>
            </div>
            <button onclick="location.reload()" style="background: var(--accent-orange); color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-weight: 500;">🔄 刷新数据</button>
        </div>
        
        <div class="stats-row">
            <div class="stat-box">
                <div class="stat-value">{{ stats['count'] }}</div>
                <div class="stat-label">回测数量</div>
            </div>
            <div class="stat-box">
                <div class="stat-value {{ 'return-positive' if stats['avg_return'] >= 0 else 'return-negative' }}">{{ "{:.1f}".format(stats['avg_return']) }}%</div>
                <div class="stat-label">平均收益</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ "{:.2f}".format(stats['avg_sharpe']) }}</div>
                <div class="stat-label">平均夏普</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ stats['win_rate'] }}%</div>
                <div class="stat-label">胜率</div>
            </div>
            {% if stats['best'] %}
            <div class="stat-box">
                <div class="stat-value return-positive">{{ stats['best']['symbol'] }}</div>
                <div class="stat-label">最佳: +{{ "{:.1f}".format(stats['best']['total_return']) }}%</div>
            </div>
            {% endif %}
        </div>
        
        <div class="main-grid">
            <div class="card">
                <div class="card-title">📊 收益分布</div>
                <div class="chart-wrapper">
                    <canvas id="returnDist"></canvas>
                </div>
            </div>
            <div class="card">
                <div class="card-title">📈 夏普比率分布</div>
                <div class="chart-wrapper">
                    <canvas id="sharpeDist"></canvas>
                </div>
            </div>
        </div>
        
        <div class="results-table">
            <div class="table-header">
                <h3 style="font-size: 18px; font-weight: 600;">📋 回测结果详情</h3>
                <input type="text" class="search-input" id="searchBox" placeholder="搜索股票代码..." onkeyup="filterTable()">
            </div>
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th>股票</th>
                        <th>收益率</th>
                        <th>夏普比率</th>
                        <th>最大回撤</th>
                        <th>胜率</th>
                        <th>交易次数</th>
                        <th>评级</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in results %}
                    <tr>
                        <td><strong>{{ r['symbol'] }}</strong></td>
                        <td class="{{ 'return-positive' if r['total_return'] >= 0 else 'return-negative' }}">{{ "{:.2f}".format(r['total_return']) }}%</td>
                        <td>{{ "{:.2f}".format(r.get('sharpe_ratio', 0)) }}</td>
                        <td>{{ "{:.1f}".format(r.get('max_drawdown', 0)) }}%</td>
                        <td>{{ "{:.1f}".format(r.get('win_rate', 0)) }}%</td>
                        <td>{{ r.get('total_trades', 0) }}</td>
                        <td>
                            {% set ret = r['total_return'] %}
                            {% set sharpe = r.get('sharpe_ratio', 0) %}
                            {% if ret >= 20 and sharpe >= 1.5 %}
                            <span class="grade grade-a">A级</span>
                            {% elif ret >= 0 and sharpe >= 1 %}
                            <span class="grade grade-b">B级</span>
                            {% else %}
                            <span class="grade grade-c">C级</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align: center; padding: 60px; color: var(--text-secondary);">暂无回测数据，请先执行批量回测</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        const results = {{ results_json | safe }};
        
        // 收益分布直方图
        const returns = results.map(r => r.total_return);
        const buckets = { '亏损>20%': 0, '亏损0-20%': 0, '盈利0-20%': 0, '盈利20-50%': 0, '盈利>50%': 0 };
        returns.forEach(r => {
            if (r < -20) buckets['亏损>20%']++;
            else if (r < 0) buckets['亏损0-20%']++;
            else if (r < 20) buckets['盈利0-20%']++;
            else if (r < 50) buckets['盈利20-50%']++;
            else buckets['盈利>50%']++;
        });
        
        new Chart(document.getElementById('returnDist'), {
            type: 'bar',
            data: {
                labels: Object.keys(buckets),
                datasets: [{
                    data: Object.values(buckets),
                    backgroundColor: ['#ef4444', '#f87171', '#4ade80', '#22c55e', '#16a34a'],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { grid: { color: 'rgba(148, 163, 184, 0.1)' }, ticks: { color: '#94a3b8' } },
                    x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 11 } } }
                }
            }
        });
        
        // 夏普比率散点图
        new Chart(document.getElementById('sharpeDist'), {
            type: 'scatter',
            data: {
                datasets: [{
                    label: '股票',
                    data: results.map(r => ({ x: r.total_return, y: r.sharpe_ratio || 0 })),
                    backgroundColor: results.map(r => r.total_return >= 0 ? '#22c55e' : '#ef4444'),
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: '收益率 (%)', color: '#94a3b8' }, grid: { color: 'rgba(148, 163, 184, 0.1)' }, ticks: { color: '#94a3b8' } },
                    y: { title: { display: true, text: '夏普比率', color: '#94a3b8' }, grid: { color: 'rgba(148, 163, 184, 0.1)' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
        
        function filterTable() {
            const input = document.getElementById('searchBox').value.toUpperCase();
            const rows = document.querySelectorAll('#resultsTable tbody tr');
            rows.forEach(row => {
                const symbol = row.cells[0]?.textContent?.toUpperCase() || '';
                row.style.display = symbol.includes(input) ? '' : 'none';
            });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    results = load_results()
    stats = calc_stats(results)
    return render_template_string(HTML, results=results, results_json=json.dumps(results), stats=stats)

if __name__ == '__main__':
    print("🚀 启动回测分析 (端口 5002)")
    app.run(host='0.0.0.0', port=5002, debug=False)
