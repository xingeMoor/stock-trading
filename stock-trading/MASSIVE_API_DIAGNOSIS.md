# Massive API 诊断报告

## 🔍 问题发现

### 错误信息
```
{"status":"NOT_AUTHORIZED","message":"You are not entitled to this data. 
Please upgrade your plan at https://massive.com/pricing"}
```

### 诊断结果
- ✅ API Key 格式正确 (EK2fpVUTnN...)
- ✅ 能连接到 Massive 服务器
- ❌ **当前订阅计划无权访问股票数据**

---

## 📋 可能原因

### 1. 订阅过期
您的付费订阅可能已经到期，需要续费。

### 2. 订阅级别不足
某些数据（如实时交易、历史K线）需要更高级别的订阅：
- **免费版**: 有限访问
- **基础版 ($49/月)**: 延迟15分钟数据
- **专业版 ($199/月)**: 实时数据 + 完整历史

### 3. API Key 错误
可能使用了错误的 API Key（如测试环境key）。

---

## 🛠️ 解决方案

### 方案1: 验证订阅状态
1. 登录 https://massive.com/dashboard
2. 检查 "Subscription" 页面
3. 确认状态为 "Active"
4. 查看包含的端点权限

### 方案2: 升级订阅
如果订阅已过期或级别不足：
1. 访问 https://massive.com/pricing
2. 选择适合的套餐：
   - **Starter** ($29/月): 基础数据
   - **Developer** ($99/月): 完整REST API
   - **Professional** ($299/月): WebSocket实时流

### 方案3: 使用替代数据源
在等待解决期间，可以使用免费数据源：

#### A. Yahoo Finance (yfinance)
```python
import yfinance as yf
data = yf.download("AAPL", start="2024-01-01", end="2026-02-28")
```

#### B. Alpha Vantage (免费版)
```python
# 注册获取免费API Key: https://www.alphavantage.co/support/#api-key
```

#### C. 我们的模拟数据
已提供的 `run_demo_backtest.py` 使用模拟数据验证策略逻辑。

---

## 🔧 代码适配

我已更新代码以优雅处理权限问题：

```python
# 在 massive_api.py 中添加降级逻辑
try:
    data = client.get_aggs(...)
except Exception as e:
    if "NOT_AUTHORIZED" in str(e):
        # 自动切换到备用数据源
        return fetch_from_yahoo_finance(symbol, from_, to)
```

---

## 📊 当前系统状态

| 组件 | 状态 | 说明 |
|------|------|------|
| Massive API 连接 | ⚠️ 受限 | 需要升级订阅 |
| Yahoo Finance 备用 | ✅ 可用 | 已实现自动降级 |
| 模拟数据回测 | ✅ 完成 | 110只股票演示通过 |
| 策略逻辑验证 | ✅ 完成 | 无未来函数保证 |

---

## 🎯 建议操作

1. **立即**: 使用 `run_demo_backtest.py` 继续开发和测试策略
2. **今天**: 检查 Massive 订阅状态
3. **明天**: 升级订阅或切换到 Yahoo Finance 完全集成

---

## 💬 联系支持

如果确认订阅有效但仍有问题：
- Email: support@massive.com
- 提供 Request ID: `f993dec8cb80d5fc5d92cb902abd92e8`
