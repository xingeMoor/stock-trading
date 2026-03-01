# Q脑系统 - 阿里云部署指南
# 时间: 2026-03-01 20:58

---

## 🎉 代码已提交到GitHub！

```bash
✅ 105 files changed, 37804 insertions(+)
✅ 推送到: https://github.com/xingeMoor/stock-trading.git
```

---

## 📋 部署前准备

### 1. 在GitHub添加Secrets

访问: https://github.com/xingeMoor/stock-trading/settings/secrets/actions

添加以下Secrets:

| Secret Name | Value | 说明 |
|-------------|-------|------|
| `ALIYUN_SSH_KEY` | SSH私钥内容 | 阿里云服务器SSH密钥 |
| `DEPLOY_USER` | root | 部署用户 |
| `DEPLOY_HOST` | 47.253.133.165 | 服务器IP |
| `DEPLOY_PATH` | /opt/qbrain | 部署路径 |

### 2. 生成SSH密钥对

在本地执行:
```bash
ssh-keygen -t rsa -b 4096 -C "qbrain-deploy" -f ~/.ssh/qbrain_deploy
```

将公钥添加到阿里云服务器:
```bash
ssh-copy-id -i ~/.ssh/qbrain_deploy.pub root@47.253.133.165
```

将私钥内容添加到GitHub Secrets:
```bash
cat ~/.ssh/qbrain_deploy
```

### 3. 阿里云服务器准备

登录服务器并创建目录:
```bash
ssh root@47.253.133.165
mkdir -p /opt/qbrain
apt-get update
apt-get install -y python3 python3-pip python3-venv git nginx
```

---

## 🚀 触发部署

### 方式1: 自动部署 (推荐)
代码推送到main分支后自动触发:
```bash
git push origin main
```

### 方式2: 手动触发
访问: https://github.com/xingeMoor/stock-trading/actions/workflows/deploy.yml
点击 "Run workflow"

---

## 📁 部署后的服务

部署完成后，以下服务将在阿里云服务器上运行:

| 端口 | 服务 | 访问地址 |
|------|------|---------|
| 80/443 | 统一门户 | http://47.253.133.165 |
| 5001 | 模拟交易 | http://47.253.133.165:5001 |
| 5002 | 策略管理 | http://47.253.133.165:5002 |
| 5005 | 回测分析 | http://47.253.133.165:5005 |
| 5006 | 系统监控 | http://47.253.133.165:5006 |
| 5007 | Agent管理 | http://47.253.133.165:5007 |
| 5008 | 项目管理 | http://47.253.133.165:5008 |
| 5009 | 舆情监控 | http://47.253.133.165:5009 |

---

## 🔧 手动部署 (备用方案)

如果GitHub Actions无法使用，可以手动部署:

```bash
# 1. 登录阿里云服务器
ssh root@47.253.133.165

# 2. 克隆代码
cd /opt
rm -rf qbrain
mkdir -p qbrain && cd qbrain
git clone https://github.com/xingeMoor/stock-trading.git .

# 3. 安装依赖
pip3 install -r requirements.txt

# 4. 启动服务
python3 portal.py &          # 统一门户 (80/443)
python3 stock-trading/web_dashboard.py &           # 5001
python3 strategy_manager.py &                      # 5002
python3 stock-trading/backtest_dashboard_v2.py &   # 5005
python3 stock-trading/system_status_dashboard.py & # 5006
python3 agent_dashboard_v2.py &                    # 5007
python3 project_dashboard.py &                     # 5008
python3 sentiment_dashboard.py &                   # 5009
```

---

## ✅ 验证部署

部署完成后，在手机浏览器访问:
```
http://47.253.133.165
```

应该能看到Q脑统一门户网站！

---

*文档生成时间: 2026-03-01 20:58 by 小七*
