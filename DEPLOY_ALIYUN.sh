#!/bin/bash
# Q脑系统 - 阿里云部署脚本
# 时间: 2026-03-01
# 服务器: 47.253.133.165

set -e

echo "🚀 Q脑系统部署脚本"
echo "=================="

# 配置
SERVER_IP="47.253.133.165"
DEPLOY_DIR="/opt/qbrain"
CONDA_ENV="qbrain"
GITHUB_REPO="https://github.com/xingeMoor/stock-trading.git"

echo "📋 部署信息:"
echo "  服务器IP: $SERVER_IP"
echo "  部署目录: $DEPLOY_DIR"
echo "  Conda环境: $CONDA_ENV"
echo ""

# 1. 创建部署目录
echo "📁 步骤1: 创建部署目录..."
sudo mkdir -p $DEPLOY_DIR
sudo chown $(whoami):$(whoami) $DEPLOY_DIR
cd $DEPLOY_DIR

# 2. 克隆/更新代码
echo "📦 步骤2: 拉取最新代码..."
if [ ! -d .git ]; then
    echo "  首次部署，克隆仓库..."
    git clone $GITHUB_REPO .
else
    echo "  更新代码..."
    git fetch origin
    git reset --hard origin/main
fi

echo "  当前版本: $(git rev-parse --short HEAD)"
echo "  提交信息: $(git log -1 --pretty=format:'%s')"
echo ""

# 3. 创建Conda环境
echo "🐍 步骤3: 创建Conda环境..."
if ! conda env list | grep -q "$CONDA_ENV"; then
    echo "  创建新环境: $CONDA_ENV"
    conda create -n $CONDA_ENV python=3.10 -y
else
    echo "  环境已存在: $CONDA_ENV"
fi

# 激活环境
echo "  激活环境..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate $CONDA_ENV

# 4. 安装依赖
echo "📦 步骤4: 安装Python依赖..."
pip install --upgrade pip

# 创建requirements.txt（如果不存在）
if [ ! -f requirements.txt ]; then
    cat > requirements.txt << 'EOF'
flask>=2.0.0
pandas>=1.5.0
numpy>=1.23.0
requests>=2.28.0
python-dotenv>=0.20.0
apscheduler>=3.9.0
plotly>=5.10.0
chart.js
sqlite3
redis>=4.3.0
psycopg2-binary>=2.9.0
sqlalchemy>=1.4.0
akshare>=1.10.0
yfinance>=0.2.0
massive>=0.1.0
beautifulsoup4>=4.11.0
lxml>=4.9.0
schedule>=1.1.0
jinja2>=3.1.0
werkzeug>=2.2.0
itsdangerous>=2.1.0
click>=8.1.0
markupsafe>=2.1.0
EOF
fi

pip install -r requirements.txt

echo "  ✅ 依赖安装完成"
echo ""

# 5. 设置环境变量
echo "🔧 步骤5: 设置环境变量..."
export FLASK_ENV=production
export PYTHONPATH=$DEPLOY_DIR:$DEPLOY_DIR/stock-trading

# 6. 启动服务
echo "🚀 步骤6: 启动服务..."

# 停止旧服务
echo "  停止旧服务..."
pkill -f "portal.py" 2>/dev/null || true
pkill -f "web_dashboard.py" 2>/dev/null || true
pkill -f "strategy_manager.py" 2>/dev/null || true
pkill -f "backtest_dashboard" 2>/dev/null || true
pkill -f "system_status_dashboard" 2>/dev/null || true
pkill -f "agent_dashboard" 2>/dev/null || true
pkill -f "project_dashboard" 2>/dev/null || true
pkill -f "sentiment_dashboard" 2>/dev/null || true

sleep 2

# 启动新服务
echo "  启动新服务..."

cd $DEPLOY_DIR

# 统一门户 (80端口需要sudo)
echo "  - 启动统一门户 (80)..."
nohup sudo python3 portal.py > logs/portal.log 2>&1 &

# 5001: 模拟交易监控
echo "  - 启动模拟交易 (5001)..."
cd stock-trading
nohup python3 web_dashboard.py > ../logs/web_dashboard.log 2>&1 &
cd ..

# 5002: 策略管理
echo "  - 启动策略管理 (5002)..."
nohup python3 strategy_manager.py > logs/strategy_manager.log 2>&1 &

# 5005: 回测分析
echo "  - 启动回测分析 (5005)..."
cd stock-trading
nohup python3 backtest_dashboard_v2.py > ../logs/backtest_dashboard.log 2>&1 &
cd ..

# 5006: 系统状态监控
echo "  - 启动系统监控 (5006)..."
cd stock-trading
nohup python3 system_status_dashboard.py > ../logs/system_status_dashboard.log 2>&1 &
cd ..

# 5007: Agent管理面板
echo "  - 启动Agent管理 (5007)..."
nohup python3 agent_dashboard_v2.py > logs/agent_dashboard.log 2>&1 &

# 5008: 项目管理Dashboard
echo "  - 启动项目管理 (5008)..."
nohup python3 project_dashboard.py > logs/project_dashboard.log 2>&1 &

# 5009: 舆情监控
echo "  - 启动舆情监控 (5009)..."
nohup python3 sentiment_dashboard.py > logs/sentiment_dashboard.log 2>&1 &

echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 7. 检查服务状态
echo "✅ 步骤7: 检查服务状态..."

check_service() {
    local port=$1
    local name=$2
    if curl -s http://localhost:$port > /dev/null 2>&1; then
        echo "  ✅ $name (端口 $port) - 运行正常"
        return 0
    else
        echo "  ❌ $name (端口 $port) - 未响应"
        return 1
    fi
}

# 检查各个端口
check_service 80 "统一门户"
check_service 5001 "模拟交易"
check_service 5002 "策略管理"
check_service 5005 "回测分析"
check_service 5006 "系统监控"
check_service 5007 "Agent管理"
check_service 5008 "项目管理"
check_service 5009 "舆情监控"

echo ""
echo "🎉 部署完成！"
echo "=================="
echo "访问地址:"
echo "  统一门户: http://$SERVER_IP"
echo "  模拟交易: http://$SERVER_IP:5001"
echo "  策略管理: http://$SERVER_IP:5002"
echo "  回测分析: http://$SERVER_IP:5005"
echo "  系统监控: http://$SERVER_IP:5006"
echo "  Agent管理: http://$SERVER_IP:5007"
echo "  项目管理: http://$SERVER_IP:5008"
echo "  舆情监控: http://$SERVER_IP:5009"
echo ""
echo "日志文件: $DEPLOY_DIR/logs/"
echo "部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
