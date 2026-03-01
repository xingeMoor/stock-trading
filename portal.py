"""
Q脑统一门户 - Portal
端口：5000

功能:
- 首页导航到各个服务
- 集成5001/5002/5005/5006/5007/5008页面链接
- 现代化单页应用风格
"""
from flask import Flask, render_template_string
from datetime import datetime
import requests

app = Flask(__name__)

# 服务配置
SERVICES = [
    {
        'id': 'market',
        'name': '市场行情',
        'port': 5001,
        'icon': '📈',
        'color': '#10b981',
        'desc': '实时美股行情监控',
        'path': '/'
    },
    {
        'id': 'watchlist',
        'name': '自选股管理',
        'port': 5002,
        'icon': '⭐',
        'color': '#f59e0b',
        'desc': '股票关注列表管理',
        'path': '/'
    },
    {
        'id': 'backtest',
        'name': '策略回测',
        'port': 5005,
        'icon': '📊',
        'color': '#8b5cf6',
        'desc': '量化策略回测分析',
        'path': '/'
    },
    {
        'id': 'position',
        'name': '持仓管理',
        'port': 5006,
        'icon': '💼',
        'color': '#06b6d4',
        'desc': '投资组合与持仓跟踪',
        'path': '/'
    },
    {
        'id': 'agents',
        'name': 'Agent管理',
        'port': 5007,
        'icon': '🤖',
        'color': '#3b82f6',
        'desc': 'AI Agent状态监控',
        'path': '/'
    },
    {
        'id': 'sentiment',
        'name': '舆情监控',
        'port': 5008,
        'icon': '📰',
        'color': '#ef4444',
        'desc': '持仓股票舆情分析',
        'path': '/'
    }
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q脑 - 量化交易系统门户</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e1a;
            --bg-secondary: #111827;
            --bg-card: rgba(17, 24, 39, 0.7);
            --accent-cyan: #06b6d4;
            --accent-purple: #8b5cf6;
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
            overflow-x: hidden;
        }
        
        /* 背景动画 */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            overflow: hidden;
        }
        
        .bg-animation::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 20% 80%, rgba(6, 182, 212, 0.15) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.15) 0%, transparent 50%);
            animation: rotate 30s linear infinite;
        }
        
        @keyframes rotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* 头部 */
        .header {
            padding: 40px;
            text-align: center;
            border-bottom: 1px solid var(--border);
        }
        
        .logo {
            display: inline-flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .logo-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            box-shadow: 0 10px 40px rgba(6, 182, 212, 0.3);
        }
        
        .logo-text h1 {
            font-size: 42px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        
        .logo-text p {
            font-size: 16px;
            color: var(--text-secondary);
        }
        
        .tagline {
            font-size: 18px;
            color: var(--text-secondary);
            margin-top: 10px;
        }
        
        /* 主内容 */
        .main-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 60px 40px;
        }
        
        .section-title {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 30px;
            text-align: center;
        }
        
        /* 服务网格 */
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }
        
        .service-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
        }
        
        .service-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--service-color);
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .service-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
        }
        
        .service-card:hover::before {
            opacity: 1;
        }
        
        .service-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .service-icon {
            width: 56px;
            height: 56px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            background: var(--service-color-bg);
        }
        
        .service-info h3 {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .service-port {
            font-size: 12px;
            color: var(--text-secondary);
            font-family: monospace;
        }
        
        .service-desc {
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.6;
            margin-bottom: 20px;
            flex-grow: 1;
        }
        
        .service-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .service-status {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .service-link {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            font-weight: 500;
            color: var(--accent-cyan);
        }
        
        .service-link svg {
            width: 16px;
            height: 16px;
            transition: transform 0.3s;
        }
        
        .service-card:hover .service-link svg {
            transform: translateX(4px);
        }
        
        /* 快捷操作 */
        .quick-actions {
            margin-top: 60px;
            padding-top: 40px;
            border-top: 1px solid var(--border);
        }
        
        .actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .action-btn {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            color: var(--text-primary);
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
        }
        
        .action-btn:hover {
            background: rgba(6, 182, 212, 0.1);
            border-color: var(--accent-cyan);
            transform: translateY(-2px);
        }
        
        /* 页脚 */
        .footer {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
            font-size: 13px;
            border-top: 1px solid var(--border);
        }
        
        .footer-links {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 15px;
        }
        
        .footer-links a {
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.3s;
        }
        
        .footer-links a:hover {
            color: var(--accent-cyan);
        }
        
        /* 响应式 */
        @media (max-width: 768px) {
            .header {
                padding: 30px 20px;
            }
            
            .logo-icon {
                width: 60px;
                height: 60px;
                font-size: 30px;
            }
            
            .logo-text h1 {
                font-size: 28px;
            }
            
            .main-container {
                padding: 40px 20px;
            }
            
            .services-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    
    <!-- 头部 -->
    <header class="header">
        <div class="logo">
            <div class="logo-icon">🧠</div>
            <div class="logo-text">
                <h1>Q 脑</h1>
                <p>Q-Brain Quantitative Trading System</p>
            </div>
        </div>
        <p class="tagline">AI驱动的量化交易平台 · 智能决策 · 稳健收益</p>
    </header>
    
    <!-- 主内容 -->
    <main class="main-container">
        <h2 class="section-title">系统服务</h2>
        
        <div class="services-grid">
            {% for service in services %}
            <a href="http://localhost:{{ service.port }}{{ service.path }}" 
               class="service-card" 
               style="--service-color: {{ service.color }}; --service-color-bg: {{ service.color }}20;"
               target="_blank">
                <div class="service-header">
                    <div class="service-icon">{{ service.icon }}</div>
                    <div class="service-info">
                        <h3>{{ service.name }}</h3>
                        <span class="service-port">Port {{ service.port }}</span>
                    </div>
                </div>
                <p class="service-desc">{{ service.desc }}</p>
                <div class="service-footer">
                    <span class="service-status">
                        <span class="status-dot"></span>
                        运行中
                    </span>
                    <span class="service-link">
                        进入系统
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                        </svg>
                    </span>
                </div>
            </a>
            {% endfor %}
        </div>
        
        <!-- 快捷操作 -->
        <div class="quick-actions">
            <h2 class="section-title">快捷操作</h2>
            <div class="actions-grid">
                <a href="http://localhost:5007/api/sync" class="action-btn" target="_blank">
                    🔄 同步Agent状态
                </a>
                <a href="http://localhost:5001/api/refresh" class="action-btn" target="_blank">
                    📊 刷新市场数据
                </a>
                <a href="http://localhost:5005/api/run_backtest" class="action-btn" target="_blank">
                    🧪 运行回测
                </a>
                <button class="action-btn" onclick="checkAllStatus()">
                    🔍 检查所有服务
                </button>
            </div>
        </div>
    </main>
    
    <!-- 页脚 -->
    <footer class="footer">
        <div class="footer-links">
            <a href="https://github.com" target="_blank">GitHub</a>
            <a href="#">文档中心</a>
            <a href="#">API参考</a>
            <a href="#">帮助支持</a>
        </div>
        <p>🧠 Q 脑 (Q-Brain) 量化交易系统 · 由 小七 协助 十一郎 共同打造</p>
        <p style="margin-top: 8px; opacity: 0.6;">最后更新：{{ now }}</p>
    </footer>
    
    <script>
        // 检查所有服务状态
        async function checkAllStatus() {
            const services = {{ services|tojson }};
            let results = [];
            
            for (const service of services) {
                try {
                    const response = await fetch(`http://localhost:${service.port}/api/stats`, { 
                        method: 'GET',
                        mode: 'no-cors'
                    });
                    results.push(`${service.name}: ✅ 正常`);
                } catch (e) {
                    results.push(`${service.name}: ❌ 无法连接`);
                }
            }
            
            alert(results.join('\\n'));
        }
        
        // 添加卡片悬停效果
        document.querySelectorAll('.service-card').forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-8px)';
            });
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """门户首页"""
    return render_template_string(
        HTML_TEMPLATE,
        services=SERVICES,
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

@app.route('/api/status')
def api_status():
    """API: 获取所有服务状态"""
    status_list = []
    for service in SERVICES:
        try:
            response = requests.get(
                f"http://localhost:{service['port']}/api/stats",
                timeout=2
            )
            status_list.append({
                'id': service['id'],
                'name': service['name'],
                'port': service['port'],
                'status': 'online' if response.status_code == 200 else 'error',
                'response_time_ms': response.elapsed.total_seconds() * 1000
            })
        except Exception as e:
            status_list.append({
                'id': service['id'],
                'name': service['name'],
                'port': service['port'],
                'status': 'offline',
                'error': str(e)
            })
    
    return {
        'services': status_list,
        'total': len(status_list),
        'online': sum(1 for s in status_list if s['status'] == 'online'),
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 启动 Q 脑统一门户 (端口 {port})")
    print(f"🌐 访问地址：http://localhost:{port}")
    print("📡 集成服务：")
    for service in SERVICES:
        print(f"   • {service['name']}: http://localhost:{service['port']}")
    app.run(host='0.0.0.0', port=port, debug=False)
