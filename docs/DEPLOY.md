# QBrain 自动部署指南

本文档介绍如何配置GitHub + 阿里云的自动部署流程。

## 📋 目录

1. [快速开始](#快速开始)
2. [GitHub配置](#github配置)
3. [服务器配置](#服务器配置)
4. [Nginx配置](#nginx配置)
5. [故障排查](#故障排查)

---

## 快速开始

### 1. 配置GitHub Secrets

在GitHub仓库页面：
- 点击 `Settings` → `Secrets and variables` → `Actions`
- 添加以下Secrets：

| Secret名称 | 说明 | 值 |
|-----------|------|-----|
| `ALIYUN_SSH_KEY` | SSH私钥 | 你的SSH密钥内容 |

**生成SSH密钥：**
```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
# 复制公钥到服务器
cat ~/.ssh/github_actions.pub | ssh root@47.253.133.165 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
# 复制私钥到GitHub Secrets
cat ~/.ssh/github_actions
```

### 2. 服务器初始化

首次部署前，在服务器上执行：

```bash
# 1. 创建项目目录
mkdir -p /opt/qbrain
cd /opt/qbrain

# 2. 克隆代码（替换为你的仓库地址）
git clone https://github.com/yourusername/qbrain.git .

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建环境变量文件
cp .env.example .env
nano .env  # 编辑配置
```

### 3. 创建Systemd服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/qbrain-api.service
```

内容如下：
```ini
[Unit]
Description=QBrain API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qbrain
EnvironmentFile=/opt/qbrain/.env
ExecStart=/usr/bin/python3 /opt/qbrain/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable qbrain-api
sudo systemctl start qbrain-api
```

### 4. 测试自动部署

提交代码到main分支，观察GitHub Actions：

```bash
git add .
git commit -m "test: auto deploy"
git push origin main
```

访问 GitHub → Actions 查看部署状态。

---

## GitHub配置

### 工作流文件

已创建 `.github/workflows/deploy.yml`，功能包括：

- ✅ push到main/master分支时自动触发
- ✅ 支持手动触发(workflow_dispatch)
- ✅ 使用SSH密钥安全连接
- ✅ 自动拉取代码、安装依赖、重启服务
- ✅ 部署失败通知

### 多环境支持

如需区分staging/production环境：

1. 在GitHub Settings → Environments 创建环境
2. 为每个环境设置不同的Secrets
3. 修改workflow中的environment字段

---

## 服务器配置

### 防火墙设置

```bash
# 开放必要端口
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw allow 5001:5009/tcp  # QBrain服务
ufw enable
```

### 目录结构

```
/opt/qbrain/
├── app.py              # 主应用
├── requirements.txt    # Python依赖
├── .env               # 环境变量
├── logs/              # 日志目录
└── scripts/           # 辅助脚本
```

---

## Nginx配置

使用Nginx作为反向代理，统一入口端口：

```bash
# 安装Nginx
sudo apt update
sudo apt install nginx

# 复制配置文件
sudo cp nginx.conf /etc/nginx/sites-available/qbrain
sudo ln -s /etc/nginx/sites-available/qbrain /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# 测试并重载
sudo nginx -t
sudo systemctl reload nginx
```

配置特点：
- 80端口 → 转发到各服务端口(5001-5009)
- 支持WebSocket
- 内置速率限制
- 静态文件缓存

---

## 故障排查

### 部署失败

**问题**: GitHub Actions显示部署失败

**排查步骤**:
1. 检查Secrets是否正确设置 (`Settings → Secrets`)
2. 确认服务器IP可访问: `ping 47.253.133.165`
3. 检查SSH密钥权限: 服务器上 `~/.ssh/authorized_keys`
4. 查看详细日志: GitHub Actions页面 → 失败的job

### 服务无法启动

```bash
# 查看服务状态
sudo systemctl status qbrain-api

# 查看日志
sudo journalctl -u qbrain-api -f

# 手动测试启动
cd /opt/qbrain && python3 app.py
```

### 端口冲突

```bash
# 查看端口占用
ss -tlnp | grep 5001

# 释放端口
sudo fuser -k 5001/tcp
```

---

## 安全建议

1. **定期更换SSH密钥**
2. **使用非root用户运行服务**
3. **配置fail2ban防止暴力破解**
4. **启用阿里云安全组规则**
5. **定期备份数据和配置**

---

## 联系支持

如有问题，请检查：
- GitHub Actions日志
- 服务器系统日志: `/var/log/syslog`
- QBrain应用日志: `/opt/qbrain/logs/`
