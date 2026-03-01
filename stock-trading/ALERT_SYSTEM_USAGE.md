# 飞书通知和告警系统使用指南

## 📋 概述

本系统包含三个核心模块:
1. **alert_manager.py** - 告警管理器(级别定义、抑制、聚合、历史记录)
2. **feishu_notification.py** - 飞书通知(增强版,支持多种消息类型)
3. **notification_scheduler.py** - 通知调度器(定时任务、健康检查)

## 🔧 配置

### 1. 环境变量配置 (.env)

```bash
# ============================================
# 飞书通知配置 (二选一或都配)
# ============================================

# 方式1: Webhook (简单快速)
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxx
FEISHU_SECRET=xxxxxxxxxx  # 可选,用于签名验证

# 方式2: 自建应用 (功能更强大)
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxx
FEISHU_RECEIVE_ID=oc_xxxxxxxxxx  # 群ID或用户ID

# ============================================
# 告警系统配置
# ============================================
ALERT_ENABLED=true
DAILY_REPORT_TIME=08:00
ALERT_SUPPRESSION_MINUTES=5
```

### 2. 安装依赖

```bash
pip install apscheduler requests python-dotenv
```

## 🚀 快速开始

### 方式1: 使用便捷函数(推荐)

```python
from src.notification_scheduler import send_immediate_alert, register_tool

# 发送即时告警
send_immediate_alert(
    level="error",
    title="数据库连接失败",
    message="无法连接到主数据库服务器",
    source="database"
)

# 注册工具监控
register_tool("my_api", my_health_checker)
```

### 方式2: 直接使用各模块

```python
from src.alert_manager import get_alert_manager
from src.feishu_notification import send_system_alert, send_daily_status_report
from src.notification_scheduler import NotificationScheduler

# ===== 告警管理器 =====
manager = get_alert_manager()

# 创建告警(自动抑制重复告警)
alert = manager.create_alert(
    level="warning",
    title="磁盘空间不足",
    message="磁盘使用率超过90%",
    source="system_monitor",
    immediate=True  # 立即发送,不等待批量
)

# 获取告警统计
stats = manager.get_stats(hours=24)
print(f"24小时内告警数: {stats['total']}")

# ===== 飞书通知 =====
# 发送系统告警
send_system_alert(
    level="critical",
    title="服务宕机",
    message="交易服务无响应",
    details={"服务": "trading-api", "错误码": 500}
)

# 发送每日报告
send_daily_status_report(
    system_status={
        "uptime": "7天",
        "tools_status": {"yahoo": "up", "akshare": "up"},
        "data_freshness": "实时"
    },
    trading_summary={"total_trades": 50, "profit_loss": 1200},
    alert_summary={"total_alerts": 10, "by_level": {"warning": 8, "error": 2}}
)

# ===== 通知调度器 =====
scheduler = NotificationScheduler()

# 注册工具检查器
def check_yahoo():
    return {
        "status": "up",  # up/down
        "latency_ms": 150,
        "message": "正常",
        "last_success": "2024-01-15T10:00:00"
    }

scheduler.register_tool_checker("yahoo_finance", check_yahoo)

# 启动调度器
scheduler.start()
# 将每天8点发送报告,每5分钟检查工具健康状态
```

## 📊 功能详解

### 告警级别

| 级别 | Emoji | 用途 |
|------|-------|------|
| info | ℹ️ | 普通信息通知 |
| warning | ⚠️ | 警告,需要注意 |
| error | ❌ | 错误,需要处理 |
| critical | 🚨 | 严重故障,立即处理 |

### 告警抑制

相同告警(同level+title+source)在默认5分钟内不会重复发送,避免告警风暴。

```python
# 修改抑制时间(分钟)
manager = AlertManager(suppression_minutes=10)
```

### 告警聚合

当短时间内产生大量告警时,会自动聚合成一条汇总消息发送。

### 定时任务

```python
from src.notification_scheduler import get_scheduler

scheduler = get_scheduler()

# 自定义每日报告时间
scheduler.daily_report_time = "09:00"

# 添加备用通知方式(当飞书失败时使用)
def backup_notify(title, message):
    # 发送到邮件/短信/其他平台
    print(f"[备份通知] {title}: {message}")
    return True

scheduler.add_fallback_handler(backup_notify)

scheduler.start()
```

## 🧪 测试

运行完整测试:

```bash
python test_alert_system.py
```

单独测试各模块:

```bash
python src/alert_manager.py
python src/feishu_notification.py
python src/notification_scheduler.py
```

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `src/alert_manager.py` | 告警管理器核心代码 |
| `src/feishu_notification.py` | 飞书通知模块 |
| `src/notification_scheduler.py` | 通知调度器 |
| `.env.example` | 环境变量配置模板 |
| `test_alert_system.py` | 完整测试脚本 |
| `data/alerts.db` | 告警历史数据库(自动创建) |

## 🔍 常见问题

### Q: 飞书通知发送失败?
A: 检查以下几点:
1. `.env` 中是否正确配置了 `FEISHU_WEBHOOK` 或 `FEISHU_APP_ID/SECRET`
2. 如果使用App方式,确认 `FEISHU_RECEIVE_ID` 已设置
3. 机器人是否已被添加到目标群聊
4. 网络是否能访问飞书API

### Q: 如何查看告警历史?
A: 
```python
from src.alert_manager import get_alert_manager
manager = get_alert_manager()
history = manager.get_alert_history(limit=100)
for alert in history:
    print(f"[{alert.level}] {alert.title} - {alert.status}")
```

### Q: 如何修改定时任务时间?
A: 修改 `.env` 中的 `DAILY_REPORT_TIME`,格式为 `HH:MM`,例如 `09:30`。

### Q: APScheduler未安装怎么办?
A: 系统会自动降级使用简单调度器,但建议安装APScheduler以获得更好的性能:
```bash
pip install apscheduler
```

## 📞 技术支持

如有问题,请检查日志输出或查看源码注释。主要日志通过Python logging输出,可在控制台查看。
