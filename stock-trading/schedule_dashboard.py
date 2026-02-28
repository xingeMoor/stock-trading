"""
定时任务配置网页服务
可以在网页上配置和管理定时任务
"""
from flask import Flask, render_template_string, jsonify, request
import json
import os
from datetime import datetime

app = Flask(__name__)

# 定时任务配置文件
SCHEDULE_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'data', 'schedule_config.json')


def load_schedule_config():
    """加载定时任务配置"""
    if not os.path.exists(SCHEDULE_CONFIG_FILE):
        return get_default_config()
    
    with open(SCHEDULE_CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_schedule_config(config):
    """保存定时任务配置"""
    os.makedirs(os.path.dirname(SCHEDULE_CONFIG_FILE), exist_ok=True)
    with open(SCHEDULE_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_default_config():
    """默认配置"""
    return {
        'enabled': True,
        'symbols': ["GOOGL", "META", "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "AMZN"],
        'initial_capital': 100000,
        'strategy': "optimized_v2",
        'position_size': 0.3,
        'interval_minutes': 60,
        'market_hours': {
            'start': '21:30',  # 北京时间
            'end': '04:00',
            'timezone': 'Asia/Shanghai'
        },
        'notifications': {
            'feishu_enabled': False,
            'feishu_webhook': ''
        },
        'last_run': None,
        'next_run': None
    }


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>定时任务配置</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .header h1 { color: #333; font-size: 32px; margin-bottom: 10px; }
        .header .subtitle { color: #666; font-size: 16px; }
        .status-card {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .status-row {
            display: flex;
            justify-content: space-between;
            padding: 15px 0;
            border-bottom: 1px solid #e5e7eb;
        }
        .status-row:last-child { border-bottom: none; }
        .status-label { color: #666; font-size: 14px; }
        .status-value { font-weight: 600; color: #333; }
        .status-value.enabled { color: #10b981; }
        .status-value.disabled { color: #ef4444; }
        .form-section {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .form-section h2 {
            color: #333;
            font-size: 20px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }
        .form-group { margin-bottom: 20px; }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #374151;
            font-weight: 500;
        }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-size: 14px;
        }
        .form-group textarea { min-height: 100px; font-family: monospace; }
        .form-group small { color: #6b7280; font-size: 12px; }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .checkbox-group input[type="checkbox"] {
            width: 20px;
            height: 20px;
        }
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 30px;
        }
        .btn {
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5568d3; }
        .btn-success { background: #10b981; color: white; }
        .btn-success:hover { background: #059669; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn-secondary { background: #6b7280; color: white; }
        .btn-secondary:hover { background: #4b5563; }
        .stock-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .stock-tag {
            background: #e5e7eb;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .stock-tag button {
            background: none;
            border: none;
            cursor: pointer;
            color: #6b7280;
            font-size: 16px;
        }
        .stock-tag button:hover { color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ 定时任务配置</h1>
            <p class="subtitle">配置模拟交易定时执行参数</p>
        </div>
        
        <div class="status-card">
            <div class="status-row">
                <span class="status-label">📊 服务状态</span>
                <span class="status-value {{ 'enabled' if config.enabled else 'disabled' }}" id="serviceStatus">
                    {{ '运行中' if config.enabled else '已停止' }}
                </span>
            </div>
            <div class="status-row">
                <span class="status-label">🕐 上次执行</span>
                <span class="status-value">{{ config.last_run or '从未执行' }}</span>
            </div>
            <div class="status-row">
                <span class="status-label">🔜 下次执行</span>
                <span class="status-value">{{ config.next_run or '未设置' }}</span>
            </div>
        </div>
        
        <form id="configForm" onsubmit="saveConfig(event)">
            <div class="form-section">
                <h2>📋 基本设置</h2>
                
                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="enabled" name="enabled" {{ 'checked' if config.enabled else '' }}>
                        <label for="enabled" style="margin:0;">启用定时任务</label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>股票代码列表</label>
                    <textarea id="symbols" name="symbols" placeholder="GOOGL,META,AAPL">{{ ','.join(config.symbols) }}</textarea>
                    <small>逗号分隔的股票代码</small>
                    <div class="stock-tags" id="stockTags"></div>
                </div>
                
                <div class="form-group">
                    <label>初始资金 (美元)</label>
                    <input type="number" id="initial_capital" name="initial_capital" value="{{ config.initial_capital }}">
                </div>
            </div>
            
            <div class="form-section">
                <h2>📈 策略设置</h2>
                
                <div class="form-group">
                    <label>交易策略</label>
                    <select id="strategy" name="strategy">
                        <option value="optimized_v2" {{ 'selected' if config.strategy == 'optimized_v2' else '' }}>optimized_v2 (推荐)</option>
                        <option value="relaxed" {{ 'selected' if config.strategy == 'relaxed' else '' }}>relaxed</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>单笔仓位比例</label>
                    <input type="number" id="position_size" name="position_size" step="0.1" min="0.1" max="1.0" value="{{ config.position_size }}">
                    <small>0.3 = 30% 仓位</small>
                </div>
                
                <div class="form-group">
                    <label>执行间隔 (分钟)</label>
                    <input type="number" id="interval_minutes" name="interval_minutes" value="{{ config.interval_minutes }}">
                    <small>建议 60 分钟 (每小时执行一次)</small>
                </div>
            </div>
            
            <div class="form-section">
                <h2>📱 通知设置</h2>
                
                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="feishu_enabled" name="feishu_enabled" {{ 'checked' if config.notifications.feishu_enabled else '' }}>
                        <label for="feishu_enabled" style="margin:0;">启用飞书通知</label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>飞书 Webhook URL</label>
                    <input type="text" id="feishu_webhook" name="feishu_webhook" value="{{ config.notifications.feishu_webhook }}" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/...">
                </div>
            </div>
            
            <div class="btn-group">
                <button type="submit" class="btn btn-primary">💾 保存配置</button>
                <button type="button" class="btn btn-success" onclick="testRun()">🧪 测试运行</button>
                <button type="button" class="btn btn-secondary" onclick="resetConfig()">🔄 恢复默认</button>
                <button type="button" class="btn btn-danger" onclick="clearHistory()">🗑️ 清空历史</button>
            </div>
        </form>
    </div>
    
    <script>
        // 解析股票标签
        function updateStockTags() {
            const symbols = document.getElementById('symbols').value;
            const tags = symbols.split(',').filter(s => s.trim()).map(s => s.trim());
            
            const container = document.getElementById('stockTags');
            container.innerHTML = tags.map(symbol => 
                `<span class="stock-tag">${symbol}<button type="button" onclick="removeStock('${symbol}')">×</button></span>`
            ).join('');
        }
        
        function removeStock(symbol) {
            const symbols = document.getElementById('symbols').value;
            const tags = symbols.split(',').filter(s => s.trim() !== symbol);
            document.getElementById('symbols').value = tags.join(',');
            updateStockTags();
        }
        
        document.getElementById('symbols').addEventListener('input', updateStockTags);
        updateStockTags();
        
        async function saveConfig(event) {
            event.preventDefault();
            
            const data = {
                enabled: document.getElementById('enabled').checked,
                symbols: document.getElementById('symbols').value.split(',').filter(s => s.trim()),
                initial_capital: parseFloat(document.getElementById('initial_capital').value),
                strategy: document.getElementById('strategy').value,
                position_size: parseFloat(document.getElementById('position_size').value),
                interval_minutes: parseInt(document.getElementById('interval_minutes').value),
                notifications: {
                    feishu_enabled: document.getElementById('feishu_enabled').checked,
                    feishu_webhook: document.getElementById('feishu_webhook').value
                }
            };
            
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            if (result.status === 'success') {
                alert('✅ 配置已保存');
                location.reload();
            } else {
                alert('❌ 保存失败：' + result.error);
            }
        }
        
        function testRun() {
            if (!confirm('确定要测试运行一次吗？这将执行一次模拟交易。')) return;
            
            fetch('/api/test_run', {method: 'POST'})
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('✅ 测试运行完成');
                } else {
                    alert('❌ 测试失败：' + data.error);
                }
            });
        }
        
        function resetConfig() {
            if (!confirm('确定要恢复默认配置吗？')) return;
            
            fetch('/api/config/reset', {method: 'POST'})
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('✅ 已恢复默认配置');
                    location.reload();
                }
            });
        }
        
        function clearHistory() {
            if (!confirm('确定要清空执行历史吗？')) return;
            
            fetch('/api/history/clear', {method: 'POST'})
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('✅ 历史已清空');
                    location.reload();
                }
            });
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    config = load_schedule_config()
    return render_template_string(HTML_TEMPLATE, config=config)


@app.route('/api/config', methods=['POST'])
def api_save_config():
    data = request.json
    config = load_schedule_config()
    
    # 更新配置
    config.update(data)
    config['updated_at'] = datetime.now().isoformat()
    
    save_schedule_config(config)
    
    return jsonify({'status': 'success'})


@app.route('/api/config/reset', methods=['POST'])
def api_reset_config():
    config = get_default_config()
    save_schedule_config(config)
    return jsonify({'status': 'success'})


@app.route('/api/config')
def api_get_config():
    return jsonify(load_schedule_config())


@app.route('/api/test_run', methods=['POST'])
def api_test_run():
    """测试运行一次"""
    from src.paper_trading import run_paper_trading
    
    config = load_schedule_config()
    
    try:
        report = run_paper_trading(
            symbols=config['symbols'],
            initial_capital=config['initial_capital'],
            strategy=config['strategy'],
            position_size=config['position_size']
        )
        
        # 更新最后执行时间
        config['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_schedule_config(config)
        
        return jsonify({'status': 'success', 'report': report})
        
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})


@app.route('/api/history/clear', methods=['POST'])
def api_clear_history():
    """清空执行历史"""
    config = load_schedule_config()
    config['last_run'] = None
    config['next_run'] = None
    save_schedule_config(config)
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("⏰ 启动定时任务配置服务")
    print("="*60)
    print(f"\n🌐 访问地址：http://localhost:5004")
    print(f"💾 配置文件：{SCHEDULE_CONFIG_FILE}")
    print("\n按 Ctrl+C 停止服务\n")
    app.run(host='0.0.0.0', port=5004, debug=True)
