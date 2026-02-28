# 量化交易系统深度 Review 报告

**Review 时间**: 2026-02-27
**系统版本**: v4.0.0
**Review 范围**: 架构、模块、策略、数据流

---

## 📋 系统架构概览

```
stock-trading/
├── main.py                    # 命令行入口
├── src/
│   ├── massive_api.py         # 数据获取 (Massive API)
│   ├── sentiment_api.py       # 舆情分析 (Finviz/Reddit/分析师)
│   ├── llm_decision.py        # LLM 决策生成
│   ├── backtest.py            # 回测引擎
│   └── strategy_runner.py     # 策略迭代器
├── strategies/
│   ├── default_strategy.py    # 默认策略 (严格)
│   ├── relaxed_strategy.py    # 宽松策略 (当前使用)
│   └── optimized_strategy.py  # 优化策略 (失败)
└── data/                      # 回测结果
```

---

## 🔍 模块级 Review

### 1️⃣ massive_api.py - 数据获取层

**职责**: 从 Massive.com API 获取股票数据

**功能**:
- ✅ `get_aggs()` - K 线数据
- ✅ `get_last_trade()` - 最新成交价
- ✅ `get_all_indicators()` - 技术指标 (SMA/EMA/MACD/RSI 等)
- ✅ `get_real_time_data()` - 实时行情

**问题**:
| 问题 | 严重性 | 说明 |
|------|--------|------|
| 硬编码 API Key | 🔴 高 | `MASSIVE_API_KEY = "EK2fpVUTnN02JruqyKAPkD5YPPZe7XJW"` 直接写在代码中 |
| 无缓存机制 | 🟡 中 | 每次回测都重新请求 API，效率低 |
| 错误处理简单 | 🟡 中 | 只返回 `{"error": str}`，无详细诊断 |
| 无速率限制 | 🟡 中 | 可能导致 API 调用超限 |

**建议**:
```python
# 1. 使用环境变量
MASSIVE_API_KEY = os.getenv('MASSIVE_API_KEY')

# 2. 添加缓存
@lru_cache(maxsize=100)
def get_aggs_cached(symbol, from_, to):
    ...

# 3. 增强错误处理
class APIError(Exception):
    def __init__(self, message, status_code, details=None):
        ...
```

---

### 2️⃣ sentiment_api.py - 舆情分析层

**职责**: 收集新闻、社交、分析师情绪

**功能**:
- ✅ `get_finviz_news()` - Finviz 新闻爬取
- ✅ `get_reddit_sentiment()` - Reddit 情绪
- ✅ `get_analyst_ratings()` - 分析师评级
- ✅ `calculate_sentiment_score()` - 综合情绪评分

**问题**:
| 问题 | 严重性 | 说明 |
|------|--------|------|
| 网页爬取不稳定 | 🔴 高 | Finviz/Reddit 可能反爬，无备用方案 |
| 情绪分析过于简单 | 🔴 高 | `analyze_text_sentiment()` 只数关键词 |
| 无中文支持 | 🟡 中 | 只处理英文新闻 |
| 数据源单一 | 🟡 中 | 依赖少数几个网站 |

**当前情绪分析逻辑**:
```python
def analyze_text_sentiment(text: str) -> float:
    positive_words = ['up', 'gain', 'surge', 'beat', 'positive']
    negative_words = ['down', 'loss', 'crash', 'miss', 'negative']
    # 简单计数...
```

**建议**:
```python
# 1. 使用专业 NLP 模型
from transformers import pipeline
sentiment_analyzer = pipeline("sentiment-analysis")

# 2. 添加更多数据源
# - Twitter API
# - StockTwits
# - 财经新闻 API (Alpha Vantage, NewsAPI)

# 3. 情绪权重优化
# 新闻情绪：40%
# 社交情绪：30%
# 分析师评级：30%
```

---

### 3️⃣ llm_decision.py - LLM 决策层

**职责**: 综合数据生成交易决策

**功能**:
- ✅ `build_decision_prompt()` - 构建提示词
- ✅ `parse_llm_response()` - 解析 JSON 响应
- ✅ `make_trading_decision()` - 执行决策
- ✅ `calculate_position_size()` - 仓位计算

**问题**:
| 问题 | 严重性 | 说明 |
|------|--------|------|
| 提示词过长 | 🟡 中 | 包含所有指标，可能分散注意力 |
| 决策原则 hardcoded | 🟡 中 | RSI<30 买入等规则写死在 prompt 中 |
| 无决策历史记录 | 🟡 中 | 不记录之前的决策，无法复盘 |
| 置信度无校准 | 🟡 中 | LLM 说 0.8 置信度但实际准确率未知 |

**提示词示例**:
```python
prompt = f"""
## 技术指标
- RSI(14): {rsi}
- MACD: {macd}
...

## 决策原则:
1. RSI < 30 考虑买入
2. MACD 金叉看涨
...
"""
```

**建议**:
```python
# 1. 精简提示词，只保留关键指标
# 2. 添加决策历史
decision_history = load_history(symbol, days=30)
prompt += f"过去 30 天决策准确率：{accuracy:.1f}%"

# 3. 置信度校准
# 记录每次置信度 vs 实际结果
# 动态调整置信度阈值
```

---

### 4️⃣ backtest.py - 回测引擎

**职责**: 基于历史数据测试策略

**功能**:
- ✅ `backtest_strategy()` - 执行回测
- ✅ `calculate_metrics()` - 计算绩效指标
- ✅ 滚动指标计算
- ✅ 交易记录保存

**问题**:
| 问题 | 严重性 | 说明 |
|------|--------|------|
| 未来函数风险 | 🔴 高 | 使用当日 close 价格决策，但实际无法预知 |
| 滑点假设固定 | 🟡 中 | 固定 0.1% 滑点，实际可能更大 |
| 手续费简化 | 🟡 中 | 只考虑佣金，无印花税等 |
| 无仓位管理 | 🔴 高 | 总是全仓进出，无分批建仓 |
| 单股票测试 | 🟡 中 | 不支持多股票组合回测 |

**回测逻辑**:
```python
for date, row in df.iterrows():
    signal = strategy(row, indicators)
    if signal == 'buy' and position == 0:
        # 全仓买入
        shares = int(capital / price)
    elif signal == 'sell' and position > 0:
        # 全仓卖出
        shares = position
```

**建议**:
```python
# 1. 避免未来函数
# 使用昨日 close 计算指标，今日 open 执行交易

# 2. 动态滑点
slippage = base_slippage * volatility

# 3. 仓位管理
position_size = min(
    capital * risk_per_trade / (entry - stop_loss),
    capital * max_position_pct
)

# 4. 多股票组合
portfolio = {
    'META': {'weight': 0.4},
    'GOOGL': {'weight': 0.4},
    'CASH': {'weight': 0.2}
}
```

---

### 5️⃣ relaxed_strategy.py - 交易策略

**职责**: 生成买卖信号

**当前逻辑**:
```python
买入 (任意 1 个):
- RSI < 40
- MACD 金叉
- 价格 > SMA20

卖出 (任意 1 个):
- RSI > 60
- MACD 死叉
- 价格 < SMA20
```

**问题**:
| 问题 | 严重性 | 说明 |
|------|--------|------|
| 阈值固定 | 🔴 高 | RSI 40/60 不适合所有股票 |
| 无趋势判断 | 🔴 高 | 牛市/熊市用同一策略 |
| 无条件权重 | 🟡 中 | 3 个条件平等，实际重要性不同 |
| 无止损止盈 | 🔴 高 | 策略本身不包含风控 |
| 过度简化 | 🔴 高 | 仅靠 3 个指标无法捕捉复杂市场 |

**为什么只有 GOOGL 表现好？**

1. **GOOGL 特性**: 2025-2026 年趋势性强，适合趋势跟踪策略
2. **策略匹配**: relaxed_strategy 恰好匹配 GOOGL 的波动特性
3. **运气成分**: 9 个月数据不足以证明策略有效
4. **其他股票**: META/NVDA 在测试期内可能是震荡市

**建议**:
```python
# 1. 动态阈值
rsi_buy_threshold = 30 + volatility_adjustment
rsi_sell_threshold = 70 - volatility_adjustment

# 2. 趋势过滤
if price > sma_50:  # 只在上升趋势中做多
    if rsi < rsi_buy_threshold:
        return 'buy'

# 3. 条件权重
score = 0
if rsi < 40: score += 0.4
if macd_golden_cross: score += 0.35
if price > sma20: score += 0.25
if score >= 0.6: return 'buy'

# 4. 内置止损
stop_loss = entry_price * 0.92  # -8% 止损
take_profit = entry_price * 1.15  # +15% 止盈
```

---

### 6️⃣ strategy_runner.py - 策略迭代器

**职责**: 自动测试多股票

**功能**:
- ✅ `run_iteration_loop()` - 迭代测试
- ✅ 目标检查
- ✅ 结果排序

**问题**:
| 问题 | 严重性 | 说明 |
|------|--------|------|
| 无参数搜索 | 🟡 中 | 只测试固定策略，不优化参数 |
| 无交叉验证 | 🟡 中 | 单次回测，未分训练集/测试集 |
| 结果分析浅 | 🟡 中 | 只输出排名，无深度分析 |

**建议**:
```python
# 1. 网格搜索参数
for rsi_buy in [30, 35, 40]:
    for rsi_sell in [60, 65, 70]:
        result = backtest(..., rsi_buy, rsi_sell)

# 2. 交叉验证
train_period = "2024-01-01 to 2024-06-30"
test_period = "2024-07-01 to 2024-12-31"

# 3. 深度分析
# - 按月分析收益
# - 按市场状态分析 (牛市/熊市/震荡)
# - 最大连续亏损次数
```

---

## 🎯 核心问题总结

### 鲁棒性差的根本原因

1. **策略过度简化** 🔴
   - 仅靠 RSI+MACD+SMA 三个指标
   - 固定阈值不适应不同股票特性
   - 无市场状态识别

2. **回测缺陷** 🟡
   - 未来函数风险
   - 无仓位管理
   - 单股票全仓进出

3. **数据质量问题** 🟡
   - 舆情分析过于简单
   - 网页爬取不稳定
   - 无备用数据源

4. **无风控机制** 🔴
   - 策略层无止损
   - 无最大回撤控制
   - 无仓位限制

---

## 🚀 优化方案

### 短期优化 (1-2 天)

1. **添加动态阈值**
   ```python
   # 根据波动率调整 RSI 阈值
   atr = calculate_atr(symbol, period=14)
   volatility_factor = atr / price
   rsi_buy = 30 + volatility_factor * 10
   ```

2. **增加趋势过滤**
   ```python
   # 只在 SMA50 之上做多
   if price > sma_50 and sma_50 > sma_200:
       # 上升趋势，执行买入逻辑
   ```

3. **内置止损止盈**
   ```python
   stop_loss = entry * 0.92
   take_profit = entry * 1.15
   ```

4. **修复 API Key 管理**
   ```python
   MASSIVE_API_KEY = os.getenv('MASSIVE_API_KEY')
   ```

### 中期优化 (1 周)

1. **多策略框架**
   - 趋势策略 (当前)
   - 均值回归策略
   - 突破策略
   - 根据市场状态切换

2. **仓位管理**
   - Kelly 公式
   - 固定风险比例
   - 分批建仓/平仓

3. **组合回测**
   - 多股票同时测试
   - 相关性分析
   - 最优权重配置

4. **改进舆情分析**
   - 使用专业 NLP 模型
   - 添加更多数据源
   - 情绪权重优化

### 长期优化 (1 月+)

1. **机器学习模型**
   - 特征工程
   - 模型训练 (XGBoost/LSTM)
   - 在线学习

2. **实时交易系统**
   - WebSocket 实时数据
   - 自动执行交易
   - 监控告警

3. **风险管理系统**
   - VaR 计算
   - 压力测试
   - 黑天鹅防护

---

## 📊 下一步行动

### 优先级排序

| 优先级 | 任务 | 预计时间 | 影响 |
|--------|------|----------|------|
| 🔴 P0 | 添加动态阈值 + 趋势过滤 | 2 小时 | 高 |
| 🔴 P0 | 内置止损止盈 | 1 小时 | 高 |
| 🟡 P1 | 仓位管理 | 4 小时 | 中 |
| 🟡 P1 | 修复 API Key 管理 | 30 分钟 | 中 |
| 🟡 P1 | 改进舆情分析 | 1 天 | 中 |
| 🟢 P2 | 多策略框架 | 2 天 | 高 |
| 🟢 P2 | 组合回测 | 1 天 | 中 |

---

## 💡 结论

**当前系统状态**:
- ✅ 基础架构完整
- ✅ 回测流程跑通
- ✅ 找到 GOOGL 这只表现好的股票
- ❌ 策略鲁棒性差
- ❌ 缺乏风控机制
- ❌ 数据分析深度不足

**核心问题**: 策略过于简单，无法适应不同股票和市场环境

**建议**: 先实施短期优化 (动态阈值 + 趋势过滤 + 止损)，然后重新测试多股票，如果仍然只有个别股票表现好，说明需要更根本的策略重构 (多策略框架 + 机器学习)。

---

**Review 完成时间**: 2026-02-27
**下一步**: 等待 GX 决策优化方向
