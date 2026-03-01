# Q 脑风控与执行层使用指南

## 概述

风控与执行层是 Q 脑量化交易系统的核心组成部分，负责：
- Kelly 公式仓位计算
- 多层次风险控制
- 订单生成和执行
- 止损止盈管理
- A 股 T+1 和美股 T+0 双市场支持

## 文件结构

```
src/risk/
├── __init__.py              # 模块入口
├── risk_manager.py          # 风控核心模块
├── position_manager.py      # 仓位管理模块
├── stop_loss.py            # 止损止盈模块
├── order_executor.py       # 订单执行器
├── drawdown_control.py     # 回撤控制模块
├── risk_metrics.py         # 风险指标模块
└── test_risk_execution.py  # 集成测试

config/
└── risk_config.yaml        # 风控配置文件
```

## 快速开始

### 1. 初始化风控系统

```python
from src.risk import RiskManager, RiskConfig, MarketType

# 创建风控配置
config = RiskConfig(
    max_position_pct=0.20,      # 单标的最大仓位 20%
    kelly_fraction=0.25,        # 1/4 Kelly
    max_drawdown_pct=0.15,      # 最大回撤 15%
    market_type=MarketType.US_STOCK  # 美股市场
)

# 创建风控管理器
rm = RiskManager(config)
rm.initialize(1000000)  # 初始资金 100 万
```

### 2. 计算 Kelly 仓位

```python
# 基于策略表现计算最优仓位
kelly_pct = rm.calculate_kelly_position(
    win_rate=0.55,        # 胜率 55%
    avg_win=0.12,         # 平均盈利 12%
    avg_loss=0.06,        # 平均亏损 6%
    signal_strength=0.8,  # 信号强度 80%
    volatility=0.30       # 年化波动率 30%
)

print(f"Kelly 最优仓位：{kelly_pct:.2%}")
# 输出：Kelly 最优仓位：4.69%
```

### 3. 交易前风控检查

```python
from src.risk import TradeRequest

# 创建交易请求
trade_request = TradeRequest(
    symbol="AAPL",
    action='buy',
    quantity=100,
    price=150.0,
    sector='Technology',
    signal_strength=0.8,
    win_rate=0.55,
    avg_win=0.12,
    avg_loss=0.06
)

# 执行风控检查
result = rm.check_trade(trade_request)

if result.allowed:
    print(f"✓ 交易允许")
    print(f"建议数量：{result.suggested_quantity}")
    print(f"风险等级：{result.risk_level.value}")
else:
    print(f"✗ 交易拒绝：{result.reason}")
```

### 4. 订单生成和执行

```python
from src.risk import OrderExecutor, ExecutionConfig, OrderType, OrderSide

# 创建执行器
executor = OrderExecutor(ExecutionConfig(
    max_slippage_pct=0.01,    # 最大滑点 1%
    batch_execution=True,      # 启用批量执行
    max_batch_size=5          # 每批最多 5 个订单
))

# 创建订单
order = executor.create_order(
    symbol="AAPL",
    side=OrderSide.BUY,
    quantity=100,
    order_type=OrderType.LIMIT,
    price=150.0,
    market=MarketType.US_STOCK
)

# 提交订单（异步）
import asyncio
asyncio.run(executor.submit_order(order))

print(f"订单状态：{order.status.value}")
print(f"成交均价：${order.avg_fill_price:.2f}")
```

### 5. 批量订单执行

```python
# 创建多个订单
orders = [
    executor.create_order("AAPL", OrderSide.BUY, 100, OrderType.LIMIT, 150.0),
    executor.create_order("GOOGL", OrderSide.BUY, 50, OrderType.MARKET),
    executor.create_order("MSFT", OrderSide.BUY, 75, OrderType.LIMIT, 300.0)
]

# 批量提交
report = asyncio.run(executor.submit_batch(orders))

print(f"成交率：{report.fill_rate:.1%}")
print(f"平均滑点：{report.avg_slippage_pct:.2%}")
print(f"执行时间：{report.execution_time_ms:.0f}ms")
```

### 6. 持仓和止损管理

```python
from src.risk import StopLossType

# 添加持仓
rm.add_position(
    symbol="AAPL",
    quantity=100,
    price=150.0,
    sector='Technology',
    market=MarketType.US_STOCK
)

# 创建止损
from src.risk.stop_loss import StopLossManager, StopLossConfig
slm = StopLossManager(StopLossConfig(
    fixed_stop_loss_pct=0.08,    # 8% 固定止损
    trailing_stop_pct=0.10       # 10% 跟踪止损
))

slm.create_stop_loss(
    symbol="AAPL",
    entry_price=150.0,
    entry_date=datetime.now(),
    stop_type=StopLossType.TRAILING
)

# 更新价格并检查止损
trigger = slm.update_price("AAPL", current_price=145.0, current_date=datetime.now())

if trigger:
    print(f"止损触发！原因：{trigger['reason']}")
    print(f"触发价格：${trigger['trigger_price']:.2f}")
    print(f"盈亏：{trigger['pnl_pct']:.2%}")
```

### 7. 组合再平衡

```python
# 获取再平衡交易指令
trades = rm.rebalance_portfolio()

for trade in trades:
    print(f"{trade['symbol']}: {trade['action']} {trade['weight_change']:.2%} (${trade['trade_value']:.2f})")
```

### 8. 风险报告

```python
# 获取完整风险报告
report = rm.get_risk_report()

print(f"组合价值：${report['portfolio_value']:,.2f}")
print(f"总盈亏：${report['total_pnl']:,.2f} ({report['total_pnl_pct']:.2%})")
print(f"当前回撤：{report['drawdown']['current']:.2%}")
print(f"回撤等级：{report['drawdown']['level'].upper()}")
print(f"风险等级：{report['risk_level'].upper()}")
print(f"持仓数量：{report['position_summary']['num_positions']}")
```

## A 股 T+1 和美股 T+0 支持

### A 股 T+1 规则

```python
from src.risk import PositionManager, PositionConfig, MarketType

# 创建 A 股仓位管理器
config = PositionConfig(market_type=MarketType.A_SHARE)
pm = PositionManager(config)

# 当日买入
pm.add_position(...)
pm.record_buy_for_t1("600519.SH", 1000)  # 记录当日买入 1000 股

# 检查可卖出数量
available = pm.get_available_quantity("600519.SH")
print(f"可卖出：{available}股")  # 输出：0 股（T+1 限制）
```

### 美股 T+0 规则

```python
# 创建美股仓位管理器
config = PositionConfig(market_type=MarketType.US_STOCK)
pm = PositionManager(config)

# 当日买入可立即卖出
pm.add_position(...)
available = pm.get_available_quantity("AAPL")
print(f"可卖出：{available}股")  # 输出：全部持仓
```

## 配置参数说明

### Kelly 仓位配置 (config/risk_config.yaml)

```yaml
kelly:
  fraction: 0.25              # Kelly 分数 (0.25 = 1/4 Kelly)
  max_position_pct: 0.25      # 单标的最大仓位 25%
  min_position_pct: 0.02      # 最小仓位 2%
  max_positions: 20           # 最大持仓数量
  max_sector_exposure: 0.40   # 单行业最大敞口 40%
```

### 止损配置

```yaml
stop_loss:
  fixed_stop_loss_pct: 0.08   # 8% 固定止损
  fixed_take_profit_pct: 0.20 # 20% 固定止盈
  trailing_stop_pct: 0.10     # 10% 跟踪止损
  max_holding_days: 30        # 最大持有 30 天
  
  # 分级止损
  enable_tiered_stop: true
  tier1_loss_pct: 0.05        # 第一级 5% 减仓 50%
  tier2_loss_pct: 0.10        # 第二级 10% 清仓
```

### 回撤控制

```yaml
drawdown:
  thresholds:
    - level: 1
      drawdown_pct: 0.05      # 5% 回撤
      leverage_ratio: 0.80    # 降仓至 80%
    - level: 2
      drawdown_pct: 0.10      # 10% 回撤
      leverage_ratio: 0.50    # 降仓至 50%
    - level: 3
      drawdown_pct: 0.15      # 15% 回撤
      leverage_ratio: 0.25    # 降仓至 25%
```

## 运行测试

```bash
cd /Users/gexin/.openclaw/workspace
PYTHONPATH=/Users/gexin/.openclaw/workspace python3 src/risk/test_risk_execution.py
```

### 测试覆盖

- ✅ Kelly 仓位计算
- ✅ 交易前风控检查
- ✅ 订单生成和执行
- ✅ A 股 T+1 和美股 T+0 规则
- ✅ 止损监控
- ✅ 完整工作流程集成

## 风险等级说明

| 等级 | 分数 | 含义 | 响应措施 |
|------|------|------|----------|
| MINIMAL | 0-20 | 极低风险 | 正常交易 |
| LOW | 20-40 | 低风险 | 正常交易 |
| MEDIUM | 40-60 | 中等风险 | 谨慎交易 |
| HIGH | 60-80 | 高风险 | 降低仓位 |
| CRITICAL | 80-100 | 严重风险 | 停止交易 |

## 最佳实践

1. **始终使用 Kelly 分数**: 使用 1/4 Kelly 或 1/8 Kelly 降低风险
2. **设置合理止损**: 建议 8% 固定止损 + 10% 跟踪止损
3. **分散投资**: HHI 指数 < 0.25，有效持仓数 > 5
4. **控制回撤**: 达到 10% 回撤时主动降仓
5. **定期检查**: 每日查看风险报告，每周审查参数

## 注意事项

- A 股 T+1 限制：当日买入不可卖出
- 交易时间检查：确保在交易时间内下单
- 滑点控制：市价单可能产生滑点，建议使用限价单
- 流动性要求：避免交易成交量过低的标的

## 扩展和定制

可以通过继承基类或修改配置文件来定制风控逻辑：

```python
class CustomRiskManager(RiskManager):
    def calculate_kelly_position(self, ...):
        # 自定义 Kelly 计算逻辑
        pass
    
    def check_trade(self, trade_request):
        # 自定义风控检查
        pass
```

---

**Author:** Q 脑 Risk-Agent  
**Date:** 2026-03-01  
**Version:** 1.0.0
