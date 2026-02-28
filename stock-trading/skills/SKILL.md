# 📈 Stock Trading Skill - 美股量化交易系统

基于 Massive.com API + 舆情分析 + LLM 自主决策的量化交易系统，内置回测和策略迭代机制。

## 🎯 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     LLM 决策引擎                              │
│  (综合技术指标 + 舆情情绪 + 基本面 → 交易决策)                   │
└─────────────────────────────────────────────────────────────┘
                              ↑
         ┌────────────────────┼────────────────────┐
         ↓                    ↓                    ↓
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Massive API    │ │   舆情数据源     │ │   基本面数据     │
│  (价格/技术指标) │ │  (新闻/社交情绪) │ │  (公司财报等)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      回测系统                                │
│  (历史验证 → 绩效评估 → 策略迭代 → 再次验证)                    │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ 核心模块

### 1. 数据获取模块 (`src/massive_api.py`)

#### 价格数据
- `get_aggs()` - K 线数据 (分钟/小时/天/周/月)
- `get_last_trade()` - 最新成交价
- `get_last_quote()` - 最新买卖报价
- `get_snapshot_ticker()` - 股票快照

#### 技术指标
- `get_sma()` - 简单移动平均
- `get_ema()` - 指数移动平均
- `get_macd()` - MACD 指标
- `get_rsi()` - 相对强弱指标
- `get_stoch()` - 随机指标
- `get_cci()` - 商品通道指标
- `get_adx()` - 平均趋向指标
- `get_williams_r()` - 威廉指标

#### 公司行为
- `list_dividends()` - 分红数据
- `list_splits()` - 拆股数据
- `get_ticker_details()` - 股票详情

#### 市场数据
- `get_market_status()` - 市场状态
- `list_market_holidays()` - 市场假日

### 2. 舆情分析模块 (`src/sentiment_api.py`)

#### 数据源
- **Finviz News** - 财经新闻聚合
- **Reddit WallStreetBets** - 社交媒体情绪
- **Twitter/X** - 实时舆情 (可选)
- **Seeking Alpha** - 分析师观点

#### 功能
- `get_news_sentiment(symbol)` - 获取新闻情绪评分
- `get_social_sentiment(symbol)` - 获取社交媒体情绪
- `get_analyst_ratings(symbol)` - 获取分析师评级
- `calculate_sentiment_score(symbol)` - 综合情绪评分 (-1 到 1)

### 3. LLM 决策模块 (`src/llm_decision.py`)

#### 输入数据
```python
{
    "symbol": "AAPL",
    "current_price": 185.50,
    "technical_indicators": {
        "sma_20": 182.30,
        "ema_20": 183.10,
        "macd": 2.02,
        "macd_signal": 0.84,
        "rsi_14": 45.2,
        ...
    },
    "sentiment": {
        "news_score": 0.65,
        "social_score": 0.42,
        "analyst_rating": "Buy",
        "composite_score": 0.58
    },
    "fundamentals": {
        "market_cap": 2850000000000,
        "pe_ratio": 28.5,
        "eps": 6.52,
        ...
    },
    "portfolio": {
        "current_position": 100,
        "average_cost": 178.20,
        "available_capital": 50000
    }
}
```

#### 输出决策
```python
{
    "action": "buy",  # buy/sell/hold
    "quantity": 50,   # 交易股数
    "confidence": 0.78,
    "reasoning": "RSI 超卖 + MACD 金叉 + 正面舆情，建议加仓",
    "stop_loss": 175.00,
    "take_profit": 195.00,
    "time_horizon": "5-10 days"
}
```

### 4. 回测系统 (`src/backtest.py`)

#### 核心功能
- `backtest_strategy()` - 单策略回测
- `backtest_multi_strategy()` - 多策略对比
- `calculate_metrics()` - 绩效指标计算
- `generate_report()` - 生成回测报告

#### 绩效指标
- 总收益率 (Total Return)
- 年化收益率 (CAGR)
- 最大回撤 (Max Drawdown)
- 夏普比率 (Sharpe Ratio)
- 胜率 (Win Rate)
- 盈亏比 (Profit/Loss Ratio)
- 交易次数 (Total Trades)
- 平均持仓时间 (Avg Holding Period)

### 5. 策略迭代 (`src/strategy_runner.py`)

#### 自动迭代流程
```python
def strategy_iteration_loop():
    """
    策略迭代循环:
    1. 初始策略回测
    2. 绩效评估
    3. 如果未达标 → 复盘分析 → 调整策略
    4. 换股票继续回测
    5. 多次验证后统计有效性
    """
    pass
```

#### 收益目标配置
```python
TARGET_METRICS = {
    "min_total_return": 20.0,      # 最低总收益率 20%
    "max_drawdown": -15.0,         # 最大回撤不超过 -15%
    "min_sharpe_ratio": 1.5,       # 最低夏普比率 1.5
    "min_win_rate": 55.0,          # 最低胜率 55%
    "min_trades": 20               # 最少交易次数
}
```

## 📊 使用示例

### 示例 1: 获取完整股票分析数据

```python
from stock_trading.src.massive_api import get_real_time_data, get_all_indicators
from stock_trading.src.sentiment_api import calculate_sentiment_score

symbol = "AAPL"

# 获取价格和指标
price_data = get_real_time_data(symbol)
indicators = get_all_indicators(symbol, period=90)

# 获取舆情
sentiment = calculate_sentiment_score(symbol)

print(f"{symbol} 当前价格：${price_data['price']}")
print(f"RSI: {indicators.get('rsi_14')}")
print(f"舆情评分：{sentiment['composite_score']}")
```

### 示例 2: LLM 交易决策

```python
from stock_trading.src.llm_decision import make_trading_decision

decision = make_trading_decision(
    symbol="AAPL",
    data={...}  # 完整数据包
)

print(f"决策：{decision['action']}")
print(f"数量：{decision['quantity']} 股")
print(f"理由：{decision['reasoning']}")
```

### 示例 3: 运行回测

```python
from stock_trading.src.backtest import backtest_strategy
from stock_trading.src.strategies.default_strategy import default_strategy

result = backtest_strategy(
    symbol="AAPL",
    start_date="2024-01-01",
    end_date="2024-12-31",
    strategy_func=default_strategy,
    initial_capital=10000,
    position_size=0.5  # 每次使用 50% 资金
)

print(f"总收益率：{result['total_return']}%")
print(f"最大回撤：{result['max_drawdown']}%")
print(f"夏普比率：{result['sharpe_ratio']}")
```

### 示例 4: 策略迭代循环

```python
from stock_trading.src.strategy_runner import run_iteration_loop

# 配置目标
targets = {
    "min_return": 25.0,
    "max_drawdown": -12.0,
    "min_sharpe": 1.8
}

# 运行迭代
results = run_iteration_loop(
    symbols=["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"],
    start_date="2023-01-01",
    end_date="2024-12-31",
    targets=targets,
    max_iterations=10
)

# 输出最终有效策略
print(f"最终策略胜率：{results['final_strategy']['win_rate']}%")
print(f"平均收益率：{results['avg_return']}%")
```

## ⚙️ 配置说明

### API Key 配置
在 `src/config.py` 中设置:

```python
MASSIVE_API_KEY = "your_api_key_here"
```

### 回测参数
```python
BACKTEST_CONFIG = {
    "initial_capital": 10000,
    "commission_rate": 0.001,      # 手续费 0.1%
    "slippage": 0.0005,            # 滑点 0.05%
    "position_size": 1.0,          # 仓位比例 (1.0=全仓)
    "stop_loss_pct": 0.05,         # 止损 5%
    "take_profit_pct": 0.15        # 止盈 15%
}
```

### 舆情数据源配置
```python
SENTIMENT_CONFIG = {
    "sources": ["finviz", "reddit", "seeking_alpha"],
    "weights": {
        "news": 0.5,
        "social": 0.3,
        "analyst": 0.2
    },
    "update_frequency": "daily"
}
```

## ⚠️ 注意事项

### API 限制 (Massive Starter)
- 数据延迟：15 分钟
- 历史数据：最多 5 年
- API 调用：无限
- Trades/Quotes 数据：不可用
- 财务数据：不可用

### 交易风险
- 本系统仅供学习和研究
- 回测结果不代表未来收益
- 实盘交易需谨慎，建议先用模拟盘验证
- 日级别交易不适合高频操作

## 📁 文件结构

```
stock-trading/
├── skills/
│   └── SKILL.md              # 技能文档
├── src/
│   ├── __init__.py
│   ├── config.py             # 配置文件
│   ├── massive_api.py        # Massive API 封装
│   ├── sentiment_api.py      # 舆情数据获取
│   ├── llm_decision.py       # LLM 决策模块
│   ├── backtest.py           # 回测系统
│   └── strategy_runner.py    # 策略迭代
├── strategies/
│   ├── __init__.py
│   ├── default_strategy.py   # 默认策略
│   └── custom_strategy.py    # 自定义策略模板
├── data/                     # 数据存储
├── logs/                     # 日志文件
└── README.md                 # 使用说明
```

---

**Version**: 4.0.0 (完整量化交易系统)
**Author**: 小 X (for GX)
**Updated**: 2026-02-27
