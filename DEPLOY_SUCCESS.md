# 🎉 Q脑系统 - 阿里云部署成功！
# 时间: 2026-03-01 21:57
# 服务器: 47.253.133.165

---

## ✅ 部署状态

### 服务启动状态
| 端口 | 服务 | 状态 |
|------|------|------|
| 5001 | 模拟交易监控 | ✅ 运行中 |
| 5005 | 回测分析面板 | ✅ 运行中 |
| 5006 | 系统状态监控 | ✅ 运行中 |
| 5007 | Agent管理面板 | ✅ 运行中 |
| 5008 | 项目管理Dashboard | ✅ 运行中 |

### 防火墙配置
✅ 所有端口 5001-5009 已开放 (0.0.0.0/0)

---

## 🔧 访问地址

```
http://47.253.133.165:5001 - 模拟交易监控
http://47.253.133.165:5005 - 回测分析面板
http://47.253.133.165:5006 - 系统状态监控
http://47.253.133.165:5007 - Agent管理面板
http://47.253.133.165:5008 - 项目管理Dashboard
```

---

## 📁 部署目录

```
/opt/qbrain/
├── stock-trading/          # 核心交易模块
├── src/                    # Agent源代码
├── logs/                   # 日志文件
├── docs/                   # 文档
└── ...
```

---

## 🐍 Conda环境

```bash
source /home/admin/.bashrc
conda activate qbrain
python --version  # Python 3.10
```

---

## 📝 后续操作

如需重启服务，登录服务器执行:
```bash
ssh root@47.253.133.165
source /home/admin/.bashrc
conda activate qbrain
cd /opt/qbrain

# 重启服务
pkill -f python3
nohup python3 stock-trading/web_dashboard.py > logs/web_dashboard.log 2>&1 &
nohup python3 stock-trading/backtest_dashboard_v2.py > logs/backtest_dashboard.log 2>&1 &
nohup python3 stock-trading/system_status_dashboard.py > logs/system_status_dashboard.log 2>&1 &
nohup python3 agent_dashboard_v2.py > logs/agent_dashboard.log 2>&1 &
nohup python3 project_dashboard.py > logs/project_dashboard.log 2>&1 &
```

---

🎉 **Q脑系统已成功部署到阿里云！**
