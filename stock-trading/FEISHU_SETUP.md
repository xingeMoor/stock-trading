# 飞书通知配置指南

## 1. 创建飞书机器人

### 步骤

1. **打开飞书**
   - 进入要接收通知的群聊

2. **添加机器人**
   - 点击右上角设置 → 群机器人
   - 点击"添加机器人"
   - 选择"自定义机器人"

3. **配置机器人**
   - 名称：`量化交易助手`
   - 头像：可选
   -  webhook 地址：**复制保存** (格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxx`)

4. **安全设置** (推荐)
   - 选择"签名验证"
   - 复制签名密钥 (Secret)

---

## 2. 配置项目

### 编辑 `.env` 文件

```bash
cd /Users/gexin/.openclaw/workspace/stock-trading
nano .env
```

### 添加飞书配置

```ini
# Massive API Key
MASSIVE_API_KEY=你的 API_KEY

# 飞书通知
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/你的 webhook
FEISHU_SECRET=你的签名密钥 (如果启用了签名验证)
```

---

## 3. 测试通知

### 运行测试脚本

```bash
python3 test_feishu_notification.py
```

### 预期输出

```
✅ 飞书通知发送成功
```

---

## 4. 自动通知

### 配置定时任务后自动发送

每次定时交易任务执行后，会自动发送通知到飞书群。

### 通知内容

```
📊 模拟交易执行报告

💰 账户状态:
  总资产：$102,350.00
  总收益：$2,350.00 (+2.35%)

📝 今日交易：3 笔
  → GOOGL: 50 股 @ $185.50
  ← META: 30 股 @ $520.25 (PnL: +$450.00)
  → AAPL: 40 股 @ $178.30
```

---

## 5. 通知类型

### 交易执行通知
- 每次定时任务执行后发送
- 包含账户状态和交易明细

### 异常告警通知
- API 调用失败
- 交易执行错误
- 数据库异常

### 每日总结通知
- 收盘后发送当日总结
- 包含绩效指标

---

## 6. 自定义通知

### 在代码中发送通知

```python
from src.feishu_notification import send_notification

# 发送简单消息
send_notification("交易执行完成")

# 发送详细报告
send_notification(
    title="📊 交易报告",
    content=report_text,
    msg_type="text"  # 或 "post"/"interactive"
)
```

---

## 7. 故障排查

### 通知发送失败

1. **检查 webhook 地址**
   ```bash
   curl -X POST "https://open.feishu.cn/open-apis/bot/v2/hook/xxx" \
     -H "Content-Type: application/json" \
     -d '{"msg_type":"text","content":{"text":"test"}}'
   ```

2. **检查网络连接**
   ```bash
   ping open.feishu.cn
   ```

3. **检查签名密钥**
   - 确保 `.env` 中的 `FEISHU_SECRET` 正确
   - 签名需要时间戳计算

---

## 8. 高级用法

### 富文本消息

```python
message = {
    "msg_type": "post",
    "content": {
        "post": {
            "zh_cn": {
                "title": "交易报告",
                "content": [
                    [{"tag": "text", "text": "总资产：$100,000"}],
                    [{"tag": "text", "text": "收益：+2.5%"}]
                ]
            }
        }
    }
}
```

### 交互式卡片

支持按钮、图表等交互元素，详见飞书开放平台文档。

---

**文档版本**: 1.0  
**更新时间**: 2026-02-28
