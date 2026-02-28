"""
实盘持仓监控网页
用于真实交易账户的持仓跟踪
"""
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import json
import os

app = Flask(__name__)

# 实盘持仓数据文件
POSITIONS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'real_positions.json')
TRANSACTIONS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'real_transactions.json')


def load_real_positions():
    """加载实盘持仓"""
    if not os.path.exists(POSITIONS_FILE):
        return []
    
    with open(POSITIONS_FILE, 'r') as f:
        return json.load(f)


def save_real_positions(positions):
    """保存实盘持仓"""
    os.makedirs(os.path.dirname(POSITIONS_FILE), exist_ok=True)
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)


def load_transactions():
    """加载交易记录"""
    if not os.path.exists(TRANSACTIONS_FILE):
        return []
    
    with open(TRANSACTIONS_FILE, 'r') as f:
        return json.load(f)


def save_transactions(transactions):
    """保存交易记录"""
    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump(transactions, f, indent=2)


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>实盘持仓监控</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
        .warning {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin-top: 15px;
            border-radius: 8px;
            color: #92400e;
        }
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
        .table-container {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        table { width: 100%; border-collapse: collapse; }
        th {
            background: #f3f4f6; padding: 15px; text-align: left;
            font-weight: 600; color: #374151;
        }
        td { padding: 15px; border-bottom: 1px solid #e5e7eb; color: #4b5563; }
        tr:hover { background: #f9fafb; }
        .btn {
            padding: 8px 16px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            margin-right: 10px;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-success { background: #10b981; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #374151; }
        .form-group input, .form-group select {
            width: 100%;
            padding: 10px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 15px;
            width: 500px;
            max-width: 90%;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💼 实盘持仓监控</h1>
            <p class="subtitle">真实交易账户 | 数据手动更新</p>
            <div class="warning">
                ⚠️ <strong>注意</strong>: 此页面用于真实交易账户，请谨慎操作。数据需要手动更新或通过 API 同步。
            </div>
            <div style="margin-top:15px;">
                <button class="btn btn-primary" onclick="showAddModal()">➕ 添加持仓</button>
                <button class="btn btn-success" onclick="exportData()">📥 导出数据</button>
                <button class="btn btn-primary" onclick="location.reload()">🔄 刷新</button>
            </div>
            <p style="color:#666;font-size:14px;margin-top:10px;">更新时间：{{ last_update }}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">💰 总资产</div>
                <div class="value" id="totalValue">${{ "%.2f"|format(stats.total_value) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">📊 总盈亏</div>
                <div class="value {{ 'positive' if stats.total_pnl >= 0 else 'negative' }}">
                    ${{ "%.2f"|format(stats.total_pnl) }} ({{ "%.2f"|format(stats.total_pnl_pct) }}%)
                </div>
            </div>
            <div class="stat-card">
                <div class="label">💵 可用现金</div>
                <div class="value">${{ "%.2f"|format(stats.cash) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">📈 持仓数量</div>
                <div class="value">{{ positions|length }}</div>
            </div>
        </div>
        
        <div class="table-container">
            <h2 style="color:#333;font-size:24px;margin-bottom:20px;">📦 当前持仓</h2>
            <table>
                <thead>
                    <tr>
                        <th>股票</th>
                        <th>股数</th>
                        <th>成本价</th>
                        <th>当前价</th>
                        <th>市值</th>
                        <th>盈亏</th>
                        <th>盈亏率</th>
                        <th>操作</th>
                    </tr>
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
                        <td>
                            <button class="btn btn-danger" style="padding:4px 8px;font-size:12px;" onclick="removePosition('{{ pos.symbol }}')">删除</button>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="8" style="text-align:center;color:#999;padding:40px;">
                            暂无持仓记录
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="table-container" style="margin-top:20px;">
            <h2 style="color:#333;font-size:24px;margin-bottom:20px;">📝 交易记录</h2>
            <table>
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>股票</th>
                        <th>类型</th>
                        <th>价格</th>
                        <th>股数</th>
                        <th>金额</th>
                        <th>备注</th>
                    </tr>
                </thead>
                <tbody>
                    {% for tx in transactions[:50] %}
                    <tr>
                        <td>{{ tx.date }}</td>
                        <td><strong>{{ tx.symbol }}</strong></td>
                        <td>{{ '买入' if tx.type == 'buy' else '卖出' }}</td>
                        <td>${{ "%.2f"|format(tx.price) }}</td>
                        <td>{{ tx.shares }}</td>
                        <td>${{ "%.2f"|format(tx.value) }}</td>
                        <td>{{ tx.note or '-' }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="7" style="text-align:center;color:#999;">暂无交易记录</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- 添加持仓模态框 -->
    <div id="addModal" class="modal">
        <div class="modal-content">
            <h2 style="margin-bottom:20px;">➕ 添加持仓</h2>
            <div class="form-group">
                <label>股票代码</label>
                <input type="text" id="symbol" placeholder="例如：AAPL">
            </div>
            <div class="form-group">
                <label>股数</label>
                <input type="number" id="shares" placeholder="100">
            </div>
            <div class="form-group">
                <label>成本价</label>
                <input type="number" id="avgCost" step="0.01" placeholder="150.00">
            </div>
            <div class="form-group">
                <label>当前价</label>
                <input type="number" id="currentPrice" step="0.01" placeholder="155.00">
            </div>
            <div style="text-align:right;">
                <button class="btn" onclick="closeModal()">取消</button>
                <button class="btn btn-primary" onclick="savePosition()">保存</button>
            </div>
        </div>
    </div>
    
    <script>
        function showAddModal() {
            document.getElementById('addModal').style.display = 'flex';
        }
        
        function closeModal() {
            document.getElementById('addModal').style.display = 'none';
        }
        
        function savePosition() {
            const data = {
                symbol: document.getElementById('symbol').value.toUpperCase(),
                shares: parseInt(document.getElementById('shares').value),
                average_cost: parseFloat(document.getElementById('avgCost').value),
                current_price: parseFloat(document.getElementById('currentPrice').value)
            };
            
            fetch('/api/position', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    alert('保存失败：' + data.error);
                }
            });
        }
        
        function removePosition(symbol) {
            if (!confirm('确定删除 ' + symbol + ' 的持仓记录吗？')) return;
            
            fetch('/api/position/' + symbol, {method: 'DELETE'})
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                }
            });
        }
        
        function exportData() {
            fetch('/api/export')
            .then(res => res.json())
            .then(data => {
                const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'positions_' + new Date().toISOString().split('T')[0] + '.json';
                a.click();
            });
        }
        
        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('addModal');
            if (event.target === modal) {
                closeModal();
            }
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    positions = load_real_positions()
    transactions = load_transactions()
    
    # 计算统计
    total_value = sum(p.get('market_value', 0) for p in positions)
    total_cost = sum(p.get('average_cost', 0) * p.get('shares', 0) for p in positions)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    
    stats = {
        'total_value': total_value,
        'total_pnl': total_pnl,
        'total_pnl_pct': total_pnl_pct,
        'cash': 0  # 需要手动设置
    }
    
    return render_template_string(
        HTML_TEMPLATE,
        positions=positions,
        transactions=transactions,
        stats=stats,
        last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


@app.route('/api/positions')
def api_positions():
    return jsonify(load_real_positions())


@app.route('/api/position', methods=['POST'])
def api_add_position():
    data = request.json
    positions = load_real_positions()
    
    # 检查是否已存在
    for i, pos in enumerate(positions):
        if pos['symbol'] == data['symbol']:
            return jsonify({'status': 'error', 'error': '持仓已存在'})
    
    # 添加新持仓
    new_pos = {
        'symbol': data['symbol'],
        'shares': data['shares'],
        'average_cost': data['average_cost'],
        'current_price': data.get('current_price', data['average_cost']),
        'market_value': data['shares'] * data.get('current_price', data['average_cost']),
        'unrealized_pnl': (data.get('current_price', data['average_cost']) - data['average_cost']) * data['shares'],
        'unrealized_pnl_pct': ((data.get('current_price', data['average_cost']) / data['average_cost']) - 1) * 100,
        'entry_date': datetime.now().strftime('%Y-%m-%d')
    }
    
    positions.append(new_pos)
    save_real_positions(positions)
    
    return jsonify({'status': 'success'})


@app.route('/api/position/<symbol>', methods=['DELETE'])
def api_remove_position(symbol):
    positions = load_real_positions()
    positions = [p for p in positions if p['symbol'] != symbol]
    save_real_positions(positions)
    return jsonify({'status': 'success'})


@app.route('/api/export')
def api_export():
    return jsonify({
        'positions': load_real_positions(),
        'transactions': load_transactions(),
        'exported_at': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("💼 启动实盘持仓监控服务")
    print("="*60)
    print(f"\n🌐 访问地址：http://localhost:5003")
    print(f"💾 数据文件：{POSITIONS_FILE}")
    print("\n按 Ctrl+C 停止服务\n")
    app.run(host='0.0.0.0', port=5003, debug=True)
