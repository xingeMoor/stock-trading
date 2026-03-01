"""
回测结果展示面板 V2.0
支持多策略对比分析
"""
from flask import Flask, render_template_string, jsonify, request
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from backtest_db import BacktestDatabase
import json

app = Flask(__name__)
db = BacktestDatabase()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>回测结果分析面板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 28px; margin-bottom: 5px; }
        .header p { opacity: 0.9; }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px 40px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }
        .card-title {
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }
        .card-value {
            font-size: 36px;
            font-weight: 700;
            color: #333;
        }
        .card-value.positive { color: #10b981; }
        .card-value.negative { color: #ef4444; }
        .card-subtitle {
            font-size: 13px;
            color: #999;
            margin-top: 8px;
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin: 30px 0 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        th, td {
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        th {
            background: #f9fafb;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            color: #666;
        }
        tr:hover { background: #f9fafb; }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-success { background: #d1fae5; color: #065f46; }
        .badge-danger { background: #fee2e2; color: #991b1b; }
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .batch-selector {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .batch-list {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        .batch-tag {
            padding: 8px 16px;
            border-radius: 20px;
            background: #e5e7eb;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 14px;
        }
        .batch-tag:hover { background: #d1d5db; }
        .batch-tag.active {
            background: #667eea;
            color: white;
        }
        .comparison-table th {
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .win { color: #10b981; font-weight: 600; }
        .loss { color: #ef4444; font-weight: 600; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 回测结果分析面板</h1>
        <p>量化策略绩效分析与对比</p>
    </div>
    
    <div class="container">
        <!-- 批次选择器 -->
        <div class="batch-selector">
            <h3>选择回测批次进行对比</h3>
            <div class="batch-list" id="batchList">
                {% for batch in batches %}
                <div class="batch-tag" data-id="{{ batch.batch_id }}" onclick="selectBatch('{{ batch.batch_id }}')">
                    {{ batch.name }} ({{ batch.strategy_name }})
                </div>
                {% endfor %}
            </div>
        </div>
        
        {% if current_batch %}
        <!-- 关键指标 -->
        <div class="grid">
            <div class="card">
                <div class="card-title">平均收益</div>
                <div class="card-value {{ 'positive' if current_batch.summary.avg_return > 0 else 'negative' }}">
                    {{ "%.2f"|format(current_batch.summary.avg_return) }}%
                </div>
                <div class="card-subtitle">{{ current_batch.total_stocks }} 只股票平均</div>
            </div>
            <div class="card">
                <div class="card-title">胜率</div>
                <div class="card-value">
                    {{ "%.1f"|format(current_batch.summary.positive_count / current_batch.total_stocks * 100) }}%
                </div>
                <div class="card-subtitle">{{ current_batch.summary.positive_count }} 只正收益</div>
            </div>
            <div class="card">
                <div class="card-title">最佳表现</div>
                <div class="card-value positive">+{{ "%.2f"|format(current_batch.summary.best_return) }}%</div>
                <div class="card-subtitle">单只股票最高收益</div>
            </div>
            <div class="card">
                <div class="card-title">最差表现</div>
                <div class="card-value negative">{{ "%.2f"|format(current_batch.summary.worst_return) }}%</div>
                <div class="card-subtitle">单只股票最低收益</div>
            </div>
        </div>
        
        <!-- 行业分布图表 -->
        <div class="chart-container">
            <h3 class="section-title">行业收益分布</h3>
            <canvas id="sectorChart" height="100"></canvas>
        </div>
        
        <!-- 个股排名 -->
        <h3 class="section-title">🏆 TOP 20 表现最佳</h3>
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>股票代码</th>
                    <th>行业</th>
                    <th>总收益</th>
                    <th>年化收益</th>
                    <th>夏普比率</th>
                    <th>最大回撤</th>
                    <th>交易次数</th>
                    <th>胜率</th>
                </tr>
            </thead>
            <tbody>
                {% for item in top_performers %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td><strong>{{ item.symbol }}</strong></td>
                    <td>{{ item.sector }}</td>
                    <td class="{{ 'win' if item.total_return > 0 else 'loss' }}">
                        {{ "%.2f"|format(item.total_return) }}%
                    </td>
                    <td>{{ "%.2f"|format(item.annualized_return) }}%</td>
                    <td>{{ "%.2f"|format(item.sharpe_ratio) }}</td>
                    <td>{{ "%.2f"|format(item.max_drawdown) }}%</td>
                    <td>{{ item.trades_count }}</td>
                    <td>{{ "%.1f"|format(item.win_rate) }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <!-- 行业分析 -->
        <h3 class="section-title">📊 行业分析</h3>
        <table>
            <thead>
                <tr>
                    <th>行业</th>
                    <th>股票数量</th>
                    <th>平均收益</th>
                    <th>平均夏普</th>
                    <th>平均回撤</th>
                </tr>
            </thead>
            <tbody>
                {% for sector, stats in sectors.items() %}
                <tr>
                    <td><strong>{{ sector }}</strong></td>
                    <td>{{ stats.count }}</td>
                    <td class="{{ 'win' if stats.avg_return > 0 else 'loss' }}">
                        {{ "%.2f"|format(stats.avg_return) }}%
                    </td>
                    <td>{{ "%.2f"|format(stats.avg_sharpe) }}</td>
                    <td>{{ "%.2f"|format(stats.avg_drawdown) }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="card" style="text-align: center; padding: 60px;">
            <h3>暂无回测数据</h3>
            <p style="color: #666; margin-top: 10px;">请先运行回测脚本生成数据</p>
        </div>
        {% endif %}
    </div>
    
    <script>
        function selectBatch(batchId) {
            window.location.href = '/?batch_id=' + batchId;
        }
        
        // 高亮当前选中的批次
        const urlParams = new URLSearchParams(window.location.search);
        const currentBatchId = urlParams.get('batch_id');
        if (currentBatchId) {
            document.querySelectorAll('.batch-tag').forEach(tag => {
                if (tag.dataset.id === currentBatchId) {
                    tag.classList.add('active');
                }
            });
        }
        
        {% if sectors %}
        // 行业分布图表
        const sectorCtx = document.getElementById('sectorChart').getContext('2d');
        new Chart(sectorCtx, {
            type: 'bar',
            data: {
                labels: {{ sectors.keys()|list|tojson }},
                datasets: [{
                    label: '平均收益 (%)',
                    data: {{ sectors.values()|map(attribute='avg_return')|list|tojson }},
                    backgroundColor: {{ sectors.values()|map(attribute='avg_return')|list|tojson }}.map(v => v > 0 ? '#10b981' : '#ef4444'),
                    borderRadius: 6,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#e5e7eb' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
        {% endif %}
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """主页"""
    batches = db.get_all_batches()
    batch_id = request.args.get('batch_id')
    
    current_batch = None
    top_performers = []
    sectors = {}
    
    if batch_id:
        for b in batches:
            if b['batch_id'] == batch_id:
                current_batch = b
                break
        
        if current_batch:
            results = db.get_batch_results(batch_id)
            top_performers = results[:20]
            sectors = db.get_sector_analysis(batch_id)
    elif batches:
        # 默认显示最新的
        current_batch = batches[0]
        results = db.get_batch_results(current_batch['batch_id'])
        top_performers = results[:20]
        sectors = db.get_sector_analysis(current_batch['batch_id'])
    
    return render_template_string(
        HTML_TEMPLATE,
        batches=batches,
        current_batch=current_batch,
        top_performers=top_performers,
        sectors=sectors
    )


@app.route('/api/batches')
def api_batches():
    """API: 获取所有批次"""
    return jsonify(db.get_all_batches())


@app.route('/api/batch/<batch_id>')
def api_batch_detail(batch_id):
    """API: 获取批次详情"""
    results = db.get_batch_results(batch_id)
    sectors = db.get_sector_analysis(batch_id)
    return jsonify({
        'results': results,
        'sectors': sectors
    })


@app.route('/api/compare')
def api_compare():
    """API: 对比多个批次"""
    batch_ids = request.args.get('ids', '').split(',')
    comparison = db.get_batch_comparison(batch_ids)
    return jsonify(comparison)


if __name__ == '__main__':
    print("🚀 启动回测分析面板...")
    print("📊 访问地址: http://localhost:5005")
    app.run(host='0.0.0.0', port=5005, debug=True)
