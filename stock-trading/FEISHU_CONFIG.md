# 飞书通知配置指南

## 📋 当前配置

已配置的飞书应用信息：
- **App ID**: cli_a928f3f8fb391bcb
- **App Secret**: K2ZFIbQ16II8KrcUwBMgEbOMqBH3P7sy

---

## 🔧 配置步骤

### 方式 1: 使用 Webhook (推荐，简单)

适合：群机器人通知

#### 1. 在飞书群中添加机器人

1. 打开飞书，进入要接收通知的群
2. 点击右上角设置 → 群机器人
3. 点击"添加机器人" → 选择"自定义机器人"
4. 填写名称：`量化交易助手`
5. 复制 **Webhook 地址** (格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxx`)

#### 2. 配置到项目

编辑 `.env` 文件：
```ini
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/你的 webhook
```

#### 3. 测试
```bash
cd /Users/gexin/.openclaw/workspace/stock-trading
python3 src/feishu_notification.py
```

---

### 方式 2: 使用自建应用 (已配置)

适合：需要更多功能 (如发送私聊、富文本等)

#### 当前状态
✅ App ID 和 Secret 已配置到 `.env` 文件

#### 需要额外配置

1. **获取群 ID**
   - 在飞书群中查看群信息
   - 群 ID 格式：`oc_xxxxxxxxxxxx`

2. **配置群 ID 到代码**
   
   编辑 `src/feishu_notification.py` 或 `scheduled_trading.py`：
   ```python
   FEISHU_CHAT_ID = "oc_你的群 ID"
   ```

3. **应用权限配置** (需要在飞书开放平台)
   - 添加权限：`im:message`
   - 添加权限：`im:chat`

---

## 🧪 测试通知

### 测试脚本

```bash
cd /Users/gexin/.openclaw/workspace/stock-trading
python3 test_feishu.py
```

### 预期输出

```
✅ 获取飞书 access token 成功
✅ 飞书通知发送成功
```

---

## 📱 通知内容示例

### 交易执行报告
```
📊 模拟交易执行报告

💰 账户状态:
  总资产：$102,350.00
  总收益：$2,350.00 (+2.35%)

📝 今日交易：3 笔
  → GOOGL: 50 股 @ $185.50
  ← META: 30 股 @ $520.25 (PnL: +$450.00)
  → AAPL: 40 股 @ $178.30

⏰ 更新时间：2026-02-28 10:30:00
```

### 异常告警
```
⚠️ 交易执行异常

错误信息：API 调用失败
股票代码：AAPL
时间：2026-02-28 10:30:00
```

---

## 🔗 集成到定时任务

编辑 `scheduled_trading.py`，在交易执行后添加：

```python
from src.feishu_notification import send_trading_report

# 执行交易
report = runner.execute_daily_trading(symbols)

# 发送飞书通知
send_trading_report(report)
```

---

## ⚠️ 常见问题

### 1. "access token 获取失败"
- 检查 App ID 和 Secret 是否正确
- 检查网络连接
- 确认应用已发布

### 2. "消息发送失败：no permission"
- 在飞书开放平台添加相应权限
- 等待权限生效 (约 5 分钟)

### 3. "机器人未添加到群"
- 使用 Webhook 方式需要手动添加机器人到群
- 使用自建应用方式需要群 ID

---

## 📚 更多资源

- 飞书开放平台：https://open.feishu.cn/
- API 文档：https://open.feishu.cn/document/ukTMukTMukTM/uEjNwUjLxYDM14SM2ATN

---

**更新时间**: 2026-02-28
