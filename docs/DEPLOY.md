# QBrain 自动部署指南

## 📋 概述

本文档描述 QBrain 项目的自动部署流程，包括 GitHub Actions 配置、服务器设置和部署操作指南。

## 🏗️ 架构

```
GitHub Push → GitHub Actions → SSH → 阿里云服务器 → 自动部署
```

## 🔧 初始设置

### 1. 服务器端配置

#### 1.1 创建部署目录

```bash
# 登录阿里云服务器
ssh root@47.253.133.165

# 创建部署目录
mkdir -p /opt/qbrain
chown -R root:root /opt/qbrain

# 克隆代码仓库
cd /opt/qbrain
git clone https://github.com/yourusername/qbrain.git .
```

#### 1.2 配置 SSH 密钥认证（推荐）

**在服务器上生成部署专用密钥：**

```bash
# 生成密钥对（如果不存在）
ssh-keygen -t ed25519 -C "deploy@qbrain" -f /root/.ssh/deploy_key -N ""

# 查看公钥
cat /root/.ssh/deploy_key.pub
```

**将公钥添加到 authorized_keys：**

```bash
cat /root/.ssh/deploy_key.pub >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

**私钥用于 GitHub Secrets（见下文）**

#### 1.3 配置 Systemd 服务

创建 `/etc/systemd/system/qbrain-api.service`：

```ini
[Unit]
Description=QBrain API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qbrain
Environment=PYTHONPATH=/opt/qbrain
EnvironmentFile=/opt/qbrain/.env
ExecStart=/usr/bin/python3 -m uvicorn api.main:app --host 0.0.0.0 --port 5001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

创建 `/etc/systemd/system/qbrain-worker.service`：

```ini
[Unit]
Description=QBrain Worker Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qbrain
Environment=PYTHONPATH=/opt/qbrain
EnvironmentFile=/opt/qbrain/.env
ExecStart=/usr/bin/python3 -m celery -A tasks worker --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
systemctl daemon-reload
systemctl enable qbrain-api qbrain-worker
systemctl start qbrain-api qbrain-worker
```

#### 1.4 配置 Nginx

```bash
# 安装 nginx
apt-get update && apt-get install -y nginx

# 复制配置文件
cp /opt/qbrain/nginx.conf /etc/nginx/sites-available/qbrain
ln -sf /etc/nginx/sites-available/qbrain /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试并重载
nginx -t
systemctl reload nginx
```

### 2. GitHub 配置

#### 2.1 添加 Secrets

进入 GitHub 仓库 → Settings → Secrets and variables → Actions

添加以下 Secrets：

| Secret Name | Value | Description |
|------------|-------|-------------|
| `ALIYUN_SSH_KEY` | 私钥内容 | `/root/.ssh/deploy_key` 的完整内容 |
| `DEPLOY_PATH` | `/opt/qbrain` | 服务器上的部署路径 |

**获取私钥内容：**

```bash
cat /root/.ssh/deploy_key
```

复制全部内容（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）

#### 2.2 配置分支保护（可选）

Settings → Branches → Add rule
- 保护 `main` 分支
- 要求 pull request 审查
- 要求状态检查通过

## 🚀 部署流程

### 自动部署

当代码推送到 `main` 或 `master` 分支时，自动触发部署：

```bash
git add .
git commit -m "Your changes"
git push origin main
```

GitHub Actions 会自动执行：
1. 检出代码
2. 建立 SSH 连接
3. 拉取最新代码
4. 安装依赖
5. 重启服务

### 手动部署

在 GitHub 仓库页面：
1. Actions → Deploy to Aliyun
2. Run workflow

或在服务器上直接运行：

```bash
ssh root@47.253.133.165
cd /opt/qbrain
./scripts/deploy.sh
```

## 📊 监控与日志

### 查看部署日志

```bash
# GitHub Actions 日志
# 在 GitHub 仓库 → Actions 中查看

# 服务器部署日志
tail -f /var/log/qbrain-deploy.log

# 服务日志
journalctl -u qbrain-api -f
journalctl -u qbrain-worker -f
```

### 检查服务状态

```bash
systemctl status qbrain-api
systemctl status qbrain-worker
```

## 🔄 回滚

如果部署失败，脚本会自动回滚到上一个备份。

手动回滚：

```bash
ssh root@47.253.133.165

# 查看最新备份
ls -lt /opt/backups/qbrain/

# 手动恢复
cd /opt/qbrain
tar -xzf /opt/backups/qbrain/qbrain-YYYYMMDD-HHMMSS.tar.gz --overwrite
systemctl restart qbrain-api qbrain-worker
```

## 🔒 安全注意事项

1. **SSH 密钥**：使用专用部署密钥，不要复用个人 SSH 密钥
2. **Secrets**：所有敏感信息存储在 GitHub Secrets 中
3. **防火墙**：仅开放必要端口（80, 443, 22）
4. **日志脱敏**：部署日志中不包含密码等敏感信息
5. **定期轮换**：建议每 3-6 个月轮换一次 SSH 密钥

## 🐛 故障排除

### 部署失败

1. 检查 GitHub Actions 日志
2. 验证 SSH 密钥是否正确配置
3. 检查服务器磁盘空间：`df -h`
4. 检查服务状态：`systemctl status qbrain-*`

### 服务无法启动

```bash
# 查看详细错误
journalctl -u qbrain-api -n 100 --no-pager

# 检查端口占用
netstat -tlnp | grep 5001

# 检查 Python 环境
python3 --version
pip list | grep -E "(fastapi|uvicorn|celery)"
```

### 权限问题

```bash
# 修复权限
chown -R root:root /opt/qbrain
chmod -R 755 /opt/qbrain
chmod +x /opt/qbrain/scripts/*.sh
```

## 📞 联系支持

如有问题，请联系运维团队或提交 Issue。
