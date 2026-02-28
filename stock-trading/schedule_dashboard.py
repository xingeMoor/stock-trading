"""
定时任务配置 - 现代化深色主题
"""
from flask import Flask, render_template_string, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'data', 'schedule_config.json')

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            'enabled': True, 'symbols': ['GOOGL','META','AAPL'], 
            'capital': 100000, 'strategy': 'optimized_v2', 
            'position_size': 0.3, 'interval': 60
        }
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Scheduler | 定时任务配置</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0a0f1c; --card: #111827; --accent: #06b6d4; --green: #10b981; --text: #f1f5f9; --muted: #64748b; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
        .container { max-width: 800px; margin: 0 auto; padding: 40px 24px; }
        .header { text-align: center; margin-bottom: 48px; }
        .header h1 { font-size: 36px; font-weight: 800; background: linear-gradient(135deg, var(--accent), #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .form-card { background: var(--card); border-radius: 20px; padding: 32px; margin-bottom: 24px; }
        .form-title { font-size: 18px; font-weight: 600; margin-bottom: 24px; display: flex; align-items: center; gap: 10px; }
        .form-group { margin-bottom: 24px; }
        label { display: block; margin-bottom: 8px; color: var(--muted); font-size: 14px; }
        input, select { width: 100%; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 12px 16px; color: var(--text); font-size: 15px; }
        .toggle { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
        .toggle-switch { width: 50px; height: 28px; background: rgba(255,255,255,0.1); border-radius: 14px; position: relative; cursor: pointer; transition: 0.3s; }
        .toggle-switch.active { background: var(--green); }
        .toggle-switch::after { content: ''; position: absolute; width: 24px; height: 24px; background: white; border-radius: 50%; top: 2px; left: 2px; transition: 0.3s; }
        .toggle-switch.active::after { left: 24px; }
        .btn-primary { background: linear-gradient(135deg, var(--accent), #8b5cf6); color: white; border: none; padding: 14px 32px; border-radius: 12px; font-weight: 600; cursor: pointer; width: 100%; font-size: 16px; }
        .status-badge { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 20px; color: var(--green); font-size: 14px; margin-bottom: 24px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ Task Scheduler</h1>
            <p style="color: var(--muted); margin-top: 8px;">配置自动交易执行参数</p>
        </div>
        
        <div class="form-card">
            <div class="form-title">📊 基本设置</div>
            <div class="toggle">
                <div class="toggle-switch {{ 'active' if config['enabled'] else '' }}" onclick="this.classList.toggle('active')"></div>
                <span>启用定时任务</span>
            </div>
            <div class="form-group">
                <label>股票代码 (逗号分隔)</label>
                <input type="text" value="{{ ','.join(config['symbols']) }}" placeholder="GOOGL,META,AAPL">
            </div>
            <div class="form-group">
                <label>初始资金 (USD)</label>
                <input type="number" value="{{ config['capital'] }}">
            </div>
        </div>
        
        <div class="form-card">
            <div class="form-title">⚙️ 策略设置</div>
            <div class="form-group">
                <label>交易策略</label>
                <select><option selected>optimized_v2</option><option>relaxed</option></select>
            </div>
            <div class="form-group">
                <label>仓位比例 (0.3 = 30%)</label>
                <input type="number" step="0.1" value="{{ config['position_size'] }}">
            </div>
            <div class="form-group">
                <label>执行间隔 (分钟)</label>
                <input type="number" value="{{ config['interval'] }}">
            </div>
        </div>
        
        <button class="btn-primary">💾 保存配置</button>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    config = load_config()
    return render_template_string(HTML, config=config)

if __name__ == '__main__':
    print("🚀 启动定时任务配置 (端口 5004)")
    app.run(host='0.0.0.0', port=5004, debug=False)
