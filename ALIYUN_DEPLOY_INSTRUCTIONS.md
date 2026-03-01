# Q脑系统 - 阿里云手动部署指南
# 时间: 2026-03-01 21:07

---

## 🚀 快速部署步骤

### 1. 登录阿里云服务器

在本地终端执行:
```bash
ssh root@47.253.133.165
# 密码: ppnn13%Gx
```

### 2. 创建部署目录并拉取代码

```bash
# 创建目录
mkdir -p /opt/qbrain
cd /opt/qbrain

# 克隆代码
git clone https://github.com/xingeMoor/stock-trading.git .

# 或者如果已存在
cd /opt/qbrain && git pull origin main
```

### 3. 创建Conda环境

```bash
# 创建环境
conda create -n qbrain python=3.10 -y

# 激活环境
conda activate qbrain
```

### 4. 安装依赖

```bash
cd /opt/qbrain

# 安装Python包
pip install flask pandas numpy requests python-dotenv apscheduler plotly
pip install akshare yfinance beautifulsoup4 lxml schedule
```

### 5. 启动所有服务

```bash
cd /opt/qbrain

# 创建日志目录
mkdir -p logs

# 统一门户 (80端口)
nohup python3 portal.py > logs/portal.log 2>&1 &

# 5001: 模拟交易
cd stock-trading && nohup python3 web_dashboard.py > ../logs/web_dashboard.log 2>&1 &
cd ..

# 5002: 策略管理
nohup python3 strategy_manager.py > logs/strategy_manager.log 2>&1 &

# 5005: 回测分析
cd stock-trading && nohup python3 backtest_dashboard_v2.py > ../logs/backtest_dashboard.log 2>&1 &
cd ..

# 5006: 系统监控
cd stock-trading && nohup python3 system_status_dashboard.py > ../logs/system_status_dashboard.log 2>&1 &
cd ..

# 5007: Agent管理
nohup python3 agent_dashboard_v2.py > logs/agent_dashboard.log 2>&1 &

# 5008: 项目管理
nohup python3 project_dashboard.py > logs/project_dashboard.log 2>&1 &

# 5009: 舆情监控
nohup python3 sentiment_dashboard.py > logs/sentiment_dashboard.log 2>&1 &
```

### 6. 验证部署

```bash
# 检查服务是否运行
curl http://localhost:5001
curl http://localhost:5002
curl http://localhost:5005
curl http://localhost:5006
curl http://localhost:5007
curl http://localhost:5008
curl http://localhost:5009
```

### 7. 手机访问测试

在手机浏览器访问:
```
http://47.253.133.165:5001
http://47.253.133.165:5002
http://47.253.133.165:5005
http://47.253.133.165:5006
http://47.253.133.165:5007
http://47.253.253.165:5008
http://47.253.133.165:5009
```

---

## 📁 文件位置

部署脚本已生成:
- `DEPLOY_ALIYUN.sh` - 完整自动化部署脚本

可以上传到服务器执行:
```bash
scp DEPLOY_ALIYUN.sh root@47.253.133.165:/opt/
ssh root@47.253.133.165
chmod +x /opt/DEPLOY_ALIYUN.sh
bash /opt/DEPLOY_ALIYUN.sh
```

---

## 🔧 Ops-Agent状态

Ops-Agent仍在运行中(49分钟)，正在配置GitHub Actions自动部署。

由于需要SSH密钥配置，建议先使用上述手动部署方式，后续再切换到自动部署。

---

*文档生成时间: 2026-03-01 21:07 by 小七*
