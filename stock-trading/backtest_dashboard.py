"""
回测结果可视化网页服务
独立于模拟交易监控
"""
from flask import Flask, render_template_string, jsonify, request
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)

# 回测结果目录
BACKTEST_DIR = os.path.join(os.path.dirname(__file__), 'data', 'backtest_results')
os.makedirs(BACKTEST_DIR, exist_ok=True)


def load_backtest_results(symbol=None, limit=100):
    """加载回测结果"""
    results = []
    
    if not os.path.exists(BACKTEST_DIR):
        return []
    
    for filename in os.listdir(BACKTEST_DIR):
        if not filename.endswith('.json'):
            continue
        
        if symbol and symbol not in filename:
            continue
        
        filepath = os.path.join(BACKTEST_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                data['_filename'] = filename
                results.append(data)
        except:
            pass
    
    # 按日期排序
    results.sort(key=lambda x: x.get('end_date', ''), reverse=True)
    
    return results[:limit]


def get_backtest_statistics():
    """获取回测统计"""
    results = load_backtest_results(limit=1000)
    
    if not results:
        return {
            'total_backtests': 0,
            'avg_return': 0,
            'avg_sharpe': 0,
            'avg_drawdown': 0,
            'win_rate': 0,
            'best_stock': None,
            'worst_stock': None
        }
    
    total_returns = [r.get('total_return', 0) for r in results]
    sharpe_ratios = [r.get('sharpe_ratio', 0) for r in results]
    drawdowns = [r.get('max_drawdown', 0) for r in results]
    
    # 找出最佳和最差
    best = max(results, key=lambda x: x.get('total_return', 0))
    worst = min(results, key=lambda x: x.get('total_return', 0))
    
    # 计算胜率 (收益率>0 的比例)
    winning = sum(1 for r in total_returns if r > 0)
    win_rate = winning / len(total_returns) * 100 if total_returns else 0
    
    return {
        'total_backtests': len(results),
        'avg_return': round(sum(total_returns) / len(total_returns), 2) if total_returns else 0,
        'avg_sharpe': round(sum(sharpe_ratios) / len(sharpe_ratios), 2) if sharpe_ratios else 0,
        'avg_drawdown': round(sum(drawdowns) / len(drawdowns), 2) if drawdowns else 0,
        'win_rate': round(win_rate, 2),
        'best_stock': {
            'symbol': best.get('symbol'),
            'return': best.get('total_return', 0)
        } if best else None,
        'worst_stock': {
            'symbol': worst.get('symbol'),
            'return': worst.get('total_return', 0)
        } if worst else None
    }


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回测结果监控</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
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
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .stat-card .label { color: #666; font-size: 13px; margin-bottom: 8px; }
        .stat-card .value { font-size: 28px; font-weight: bold; color: #333; }
        .stat-card .value.positive { color: #10b981; }
        .stat-card .value.negative { color: #ef4444; }
        .table-container {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #f3f4f6; padding: 15px; text-align: left;
            font-weight: 600; color: #374151; cursor: pointer;
        }
        th:hover { background: #e5e7eb; }
        td { padding: 15px; border-bottom: 1px solid #e5e7eb; color: #4b5563; }
        tr:hover { background: #f9fafb; }
        .badge {
            display: inline-block; padding: 4px 12px;
            border-radius: 20px; font-size: 12px; font-weight: 600;
        }
        .badge-good { background: #d1fae5; color: #065f46; }
        .badge-bad { background: #fee2e2; color: #991b1b; }
        .badge-normal { background: #e5e7eb; color: #374151; }
        .refresh-btn {
            background: #667eea; color: white; border: none;
            padding: 10px 20px; border-radius: 8px; cursor: pointer;
        }
        .refresh-btn:hover { background: #5568d3; }
        .search-box {
            padding: 10px 15px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
            width: 200px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 回测结果监控</h1>
            <p class="subtitle">回测周期：2024-01-01 至 2026-02-28 | 策略：optimized_v2</p>
            <div style="margin-top:15px;">
                <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
                <input type="text" class="search-box" id="searchInput" placeholder="搜索股票代码..." onkeyup="filterTable()">
            </div>
            <p style="color:#666;font-size:14px;margin-top:10px;">更新时间：{{ last_update }}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">📝 回测数量</div>
                <div class="value">{{ stats["total_backtests"] }}</div>
            </div>
            <div class="stat-card">
                <div class="label">📈 平均收益</div>
                <div class="value {{ 'positive' if stats["avg_return"] >= 0 else 'negative' }}">
                    {{ "%.2f"|format(stats["avg_return"]) }}%
                </div>
            </div>
            <div class="stat-card">
                <div class="label">📊 平均夏普</div>
                <div class="value {{ 'positive' if stats["avg_sharpe"] >= 1.5 else 'negative' }}">
                    {{ "%.2f"|format(stats["avg_sharpe"]) }}
                </div>
            </div>
            <div class="stat-card">
                <div class="label">📉 平均回撤</div>
                <div class="value {{ 'positive' if stats["avg_drawdown"] >= -15 else 'negative' }}">
                    {{ "%.2f"|format(stats["avg_drawdown"]) }}%
                </div>
            </div>
            <div class="stat-card">
                <div class="label">🎯 胜率</div>
                <div class="value {{ 'positive' if stats["win_rate"] >= 50 else 'negative' }}">
                    {{ "%.1f"|format(stats["win_rate"]) }}%
                </div>
            </div>
            <div class="stat-card">
                <div class="label">🏆 最佳股票</div>
                <div class="value positive">
                    {{ stats["best_stock"]["symbol"] if stats["best_stock"] else 'N/A' }}
                    <span style="font-size:16px">(+{{ "%.1f"|format(stats["best_stock"]["return"] if stats["best_stock"] else 0) }}%)</span>
                </div>
            </div>
        </div>
        
        <div class="table-container">
            <h2 style="color:#333;font-size:24px;margin-bottom:20px;">📋 回测结果列表</h2>
            <table id="backtestTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">股票</th>
                        <th onclick="sortTable(1)">回测周期</th>
                        <th onclick="sortTable(2)">收益率</th>
                        <th onclick="sortTable(3)">夏普比率</th>
                        <th onclick="sortTable(4)">最大回撤</th>
                        <th onclick="sortTable(5)">胜率</th>
                        <th onclick="sortTable(6)">交易次数</th>
                        <th>评级</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in results %}
                    <tr>
                        <td><strong>{{ r["symbol"] }}</strong></td>
                        <td>{{ r["start_date"] }} → {{ r["end_date"] }}</td>
                        <td class="{{ 'positive' if r["total_return"] >= 20 else 'negative' }}">
                            {{ "%.2f"|format(r["total_return"]) }}%
                        </td>
                        <td class="{{ 'positive' if r["sharpe_ratio"] >= 1.5 else 'negative' }}">
                            {{ "%.2f"|format(r["sharpe_ratio"]) }}
                        </td>
                        <td class="{{ 'positive' if r["max_drawdown"] >= -15 else 'negative' }}">
                            {{ "%.2f"|format(r["max_drawdown"]) }}%
                        </td>
                        <td>{{ "%.1f"|format(r["win_rate"]) }}%</td>
                        <td>{{ r["total_trades"] }}</td>
                        <td>
                            {% if r["total_return"] >= 20 and r["sharpe_ratio"] >= 1.5 and r["max_drawdown"] >= -15 %}
                            <span class="badge badge-good">优秀</span>
                            {% elif r["total_return"] >= 0 and r["sharpe_ratio"] >= 1 %}
                            <span class="badge badge-normal">合格</span>
                            {% else %}
                            <span class="badge badge-bad">较差</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="8" style="text-align:center;color:#999;padding:40px;">
                            暂无回测结果，请先执行回测
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function filterTable() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toUpperCase();
            const table = document.getElementById('backtestTable');
            const tr = table.getElementsByTagName('tr');
            
            for (let i = 1; i < tr.length; i++) {
                const td = tr[i].getElementsByTagName('td')[0];
                if (td) {
                    const txtValue = td.textContent || td.innerText;
                    tr[i].style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? '' : 'none';
                }
            }
        }
        
        function sortTable(n) {
            const table = document.getElementById('backtestTable');
            let switching = true, shouldSwitch, dir = 'asc', switchcount = 0;
            
            while (switching) {
                switching = false;
                const rows = table.rows;
                
                for (let i = 1; i < (rows.length - 1); i++) {
                    shouldSwitch = false;
                    const x = rows[i].getElementsByTagName('TD')[n];
                    const y = rows[i + 1].getElementsByTagName('TD')[n];
                    
                    let xVal = x.textContent || x.innerText;
                    let yVal = y.textContent || y.innerText;
                    
                    // 移除%符号
                    xVal = parseFloat(xVal.replace('%', '')) || xVal;
                    yVal = parseFloat(yVal.replace('%', '')) || yVal;
                    
                    if (dir === 'asc') {
                        if (xVal > yVal) { shouldSwitch = true; break; }
                    } else if (xVal < yVal) { shouldSwitch = true; break; }
                }
                
                if (shouldSwitch) {
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    switchcount++;
                } else {
                    if (switchcount === 0 && dir === 'asc') {
                        dir = 'desc';
                        switching = true;
                    }
                }
            }
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    results = load_backtest_results(limit=500)
    stats = get_backtest_statistics()
    
    return render_template_string(
        HTML_TEMPLATE,
        results=results,
        stats=stats,
        last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


@app.route('/api/results')
def api_results():
    limit = request.args.get('limit', 100, type=int)
    return jsonify(load_backtest_results(limit=limit))


@app.route('/api/statistics')
def api_stats():
    return jsonify(get_backtest_statistics())


@app.route('/api/run_backtest/<symbol>')
def api_run_backtest(symbol):
    """API: 执行单只股票回测"""
    from src.backtest import backtest_strategy
    from strategies.optimized_v2_strategy import optimized_v2_strategy
    
    result = backtest_strategy(
        symbol=symbol,
        start_date='2024-01-01',
        end_date='2026-02-28',
        strategy_func=optimized_v2_strategy,
        verbose=False
    )
    
    # 保存结果
    if 'error' not in result:
        filename = f"backtest_{symbol}_2024-01-01_2026-02-28.json"
        filepath = os.path.join(BACKTEST_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        return jsonify({'status': 'success', 'symbol': symbol, 'result': result})
    else:
        return jsonify({'status': 'error', 'symbol': symbol, 'error': result.get('error')})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("📊 启动回测结果监控服务")
    print("="*60)
    print(f"\n🌐 访问地址：http://localhost:5002")
    print(f"💾 数据目录：{BACKTEST_DIR}")
    print("\n按 Ctrl+C 停止服务\n")
    app.run(host='0.0.0.0', port=5002, debug=False)
