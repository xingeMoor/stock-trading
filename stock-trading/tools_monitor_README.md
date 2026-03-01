# Tools状态监控系统

## 概述

这是一个用于监控股票交易相关工具和服务的健康状态系统，包括：
- **美股数据API** (Massive API)
- **A股数据接口** (akshare)
- **飞书服务** (Webhook和自建应用API)

## 文件结构

```
stock-trading/
├── tools_monitor_db.py          # 数据库模块 - 表结构定义和操作
├── tools_health_checker.py      # 健康检查脚本 - 检测各类服务状态
├── tools_monitor_scheduler.py   # 定时任务调度器 - APScheduler实现
├── config.json                  # 配置文件 - 飞书相关配置
├── tools_monitor.db             # SQLite数据库文件
└── logs/                        # 日志目录
    └── scheduler.log            # 调度器运行日志
```

## 数据库表结构

### 1. tools_registry - 工具注册表
存储所有需要监控的工具信息
- `id`: 主键
- `tool_name`: 工具名称
- `tool_type`: 工具类型 (美股/A股/飞书)
- `endpoint`: 服务端点URL
- `description`: 描述
- `created_at`: 创建时间

### 2. tools_status - 工具状态历史表
记录所有工具的健康检查历史
- `id`: 主键
- `tool_id`: 关联tools_registry的外键
- `status`: 状态 (up/down)
- `response_time`: 响应时间(毫秒)
- `error_msg`: 错误信息
- `checked_at`: 检查时间

### 3. feishu_status - 飞书状态监控表
专门记录飞书相关服务的状态
- `id`: 主键
- `check_type`: 检查类型 (webhook/app)
- `status`: 状态 (up/down)
- `response_time`: 响应时间(毫秒)
- `error_msg`: 错误信息
- `checked_at`: 检查时间

## 使用方法

### 1. 初始化数据库

```bash
python3 tools_monitor_db.py
```

这将创建数据库并注册默认工具。

### 2. 配置飞书参数

编辑 `config.json` 文件：

```json
{
  "feishu_webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx",
  "feishu_app_id": "cli_xxxxx",
  "feishu_app_secret": "xxxxxxxx"
}
```

### 3. 单次运行健康检查

```bash
# 检查所有项目
python3 tools_health_checker.py

# 仅检查Tools
python3 tools_health_checker.py --tools-only

# 仅检查飞书
python3 tools_health_checker.py --feishu-only
```

### 4. 启动定时监控调度器

```bash
# 持续运行模式（每5分钟检查Tools，每10分钟检查飞书）
python3 tools_monitor_scheduler.py

# 单次运行模式
python3 tools_monitor_scheduler.py --once

# 仅检查Tools
python3 tools_monitor_scheduler.py --once --tools-only

# 仅检查飞书
python3 tools_monitor_scheduler.py --once --feishu-only
```

### 5. 查看状态记录

```bash
# 使用sqlite3命令行
sqlite3 tools_monitor.db "SELECT * FROM tools_status ORDER BY checked_at DESC LIMIT 10;"
sqlite3 tools_monitor.db "SELECT * FROM feishu_status ORDER BY checked_at DESC LIMIT 10;"
```

## 重试机制

所有检查都实现了3次重试机制：
- 首次失败后等待2秒重试
- 第二次失败后等待4秒重试
- 第三次失败后等待8秒重试
- 全部失败则记录为down状态

## 默认监控项

| 工具名称 | 类型 | 说明 |
|---------|------|------|
| massive_api | 美股 | Massive API - 美股数据源 |
| yahoo_finance | 美股 | Yahoo Finance备用数据源 |
| akshare_stock | A股 | AKShare A股实时行情 |
| akshare_index | A股 | AKShare A股指数数据 |
| feishu_webhook | 飞书 | 飞书Webhook机器人 |
| feishu_app_api | 飞书 | 飞书自建应用API |

## 日志输出

调度器的日志会同时输出到控制台和 `logs/scheduler.log` 文件。

## 停止调度器

在运行调度器的终端按 `Ctrl+C` 即可优雅停止。
