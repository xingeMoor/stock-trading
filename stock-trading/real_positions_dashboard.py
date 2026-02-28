"""
实盘持仓监控 - 现代化深色主题
"""
from flask import Flask, render_template_string, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)
POSITIONS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'real_positions.json')

def load_positions():
    if not os.path.exists(POSITIONS_FILE):
        return []
    with open(POSITIONS_FILE) as f:
        return json.load(f)

def save_positions(positions):
    os.makedirs(os.path.dirname(POSITIONS_FILE), exist_ok=True)
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)

HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Live Portfolio | 实盘持仓</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0a0f1c; --card: #111827; --accent: #ec4899; --green: #10b981; --red: #ef4444; --text: #f1f5f9; --muted: #64748b; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 32px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .header h1 { font-size: 36px; font-weight: 800; background: linear-gradient(135deg, var(--accent), #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .warning { background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); padding: 16px 20px; border-radius: 12px; margin-bottom: 32px; color: #fbbf24; font-size: 14px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .stat-card { background: var(--card); border: 1px solid rgba(255,255,255,0.05); border-radius: 16px; padding: 24px; }
        .stat-value { font-size: 32px; font-weight: 700; margin-top: 8px; }
        .positions-table { background: var(--card); border-radius: 16px; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 16px 20px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
        th { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        .btn { background: var(--accent); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; }
        .positive { color: var(--green); } .negative { color: var(--red); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💼 Live Portfolio</h1>
            <button class="btn" onclick="location.reload()">刷新</button>
        </div>
        <div class="warning">⚠️ 实盘交易账户 - 数据需手动更新或通过API同步</div>
        <div class="stats">
            <div class="stat-card"><div style="color: var(--muted); font-size: 13px;">总资产</div><div class="stat-value">$100,000</div></div>
            <div class="stat-card"><div style="color: var(--muted); font-size: 13px;">持仓数量</div><div class="stat-value">{{ positions|length }}</div></div>
        </div>
        <div class="positions-table">
            <table>
                <thead><tr><th>股票</th><th>股数</th><th>成本价</th><th>当前价</th><th>市值</th><th>盈亏</th></tr></thead>
                <tbody>
                    {% for p in positions %}
                    <tr>
                        <td><strong>{{ p.symbol }}</strong></td>
                        <td>{{ p.shares }}</td>
                        <td>${{ "{:.2f}".format(p.average_cost) }}</td>
                        <td>${{ "{:.2f}".format(p.current_price) }}</td>
                        <td>${{ "{:,.2f}".format(p.market_value) }}</td>
                        <td class="{{ 'positive' if p.unrealized_pnl >= 0 else 'negative' }}">${{ "{:,.2f}".format(p.unrealized_pnl) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="6" style="text-align: center; padding: 60px; color: var(--muted);">暂无持仓数据</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    positions = load_positions()
    return render_template_string(HTML, positions=positions)

if __name__ == '__main__':
    print("🚀 启动实盘持仓监控 (端口 5003)")
    app.run(host='0.0.0.0', port=5003, debug=False)
