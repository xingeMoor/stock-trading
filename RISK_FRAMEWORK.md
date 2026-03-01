# Q脑风险管理系统框架

## 概述

本风险管理系统是 Q脑量化交易系统的核心组成部分，旨在通过多层次、多维度的风险控制机制，保护资金安全，实现稳健收益。

## 设计理念

### 核心原则

1. **风险优先** - 在任何交易决策中，风险管理优先于收益追求
2. **多层防护** - 建立仓位、止损、回撤、指标四层防护体系
3. **动态调整** - 根据市场状态和组合表现动态调整风险参数
4. **量化驱动** - 所有风险决策基于数据和量化模型，避免主观判断
5. **自动化执行** - 风险规则系统自动执行，减少人为干预

### 风险预算框架

```
总风险预算 = 100%
├── 单一标的风险：≤ 25%
├── 单一行业风险：≤ 40%
├── 日亏损限额：≤ 3%
└── 最大回撤限额：≤ 15%
```

---

## 模块架构

```
src/risk/
├── __init__.py              # 模块入口
├── position_manager.py      # 仓位管理模块
├── stop_loss.py            # 止损止盈模块
├── drawdown_control.py     # 回撤控制模块
└── risk_metrics.py         # 风险指标模块
```

---

## 模块详解

### 1. 仓位管理模块 (PositionManager)

#### 核心功能

| 功能 | 说明 | 默认参数 |
|------|------|----------|
| Kelly 公式 | 计算最优仓位比例 | Kelly 分数 0.25 |
| 仓位限制 | 单标的/行业/总仓位上限 | 25%/40%/100% |
| 集中度控制 | HHI 指数、有效持仓数 | HHI < 0.25 |
| 动态调整 | 基于波动率和市场状态 | - |

#### Kelly 公式实现

```python
# Kelly 公式：f* = (p * b - q) / b
# 其中：p=胜率，q=1-p，b=盈亏比

def calculate_kelly_fraction(win_rate, avg_win, avg_loss):
    p = win_rate
    q = 1 - p
    b = avg_win / avg_loss
    kelly = (p * b - q) / b
    return kelly * kelly_fraction  # 使用 1/4 Kelly 降低风险
```

#### 集中度指标

- **HHI 指数**: 衡量组合集中度，HHI = Σ(weight²)
  - HHI < 0.10: 高度分散
  - HHI 0.10-0.25: 适度集中
  - HHI > 0.25: 高度集中 (风险)

- **有效持仓数**: 1/HHI，反映真实分散度

- **前 5 大集中度**: 最大 5 个持仓的权重和，建议 < 60%

#### 动态仓位调整因子

```
最终仓位 = 基础仓位 × 波动率调整 × 市场状态调整

波动率调整:
- 年化波动 > 50%: 0.5x
- 年化波动 > 30%: 0.75x
- 年化波动 < 30%: 1.0x

市场状态调整:
- 正常市场：1.0x
- 高波动市场：0.7x
- 危机市场：0.3x
```

---

### 2. 止损止盈模块 (StopLossManager)

#### 止损策略类型

| 类型 | 说明 | 适用场景 | 默认参数 |
|------|------|----------|----------|
| 固定比例止损 | 买入价下方固定百分比 | 趋势交易 | 8% |
| 跟踪止损 | 随价格上涨动态上移 | 强势趋势 | 10% 回撤 |
| 时间止损 | 超期未盈利自动退出 | 震荡市场 | 30 天 |
| 波动率止损 | 基于 ATR 动态调整 | 高波动标的 | 2×ATR |
| 技术位止损 | 关键支撑/阻力位 | 技术交易 | 自定义 |

#### 分级止损机制

```
第一级止损 (亏损 5%): 减仓 50%
第二级止损 (亏损 10%): 清仓 100%

优势:
- 避免一次性止损在低点
- 保留部分仓位等待反弹
- 降低心理负担
```

#### 跟踪止损算法

```python
def adjust_trailing_stop(current_price, highest_price):
    # 基于最高价计算新止损位
    new_stop = highest_price * (1 - trailing_stop_pct)
    
    # 只上调止损价 (更严格)
    if new_stop > current_stop:
        # 检查调整步长
        if price_change >= step_pct or days >= 5:
            stop_price = new_stop
```

#### 止盈策略

- **固定止盈**: 目标收益率 (默认 20%)
- **分级止盈**: 达到目标后分批了结
- **移动止盈**: 趋势延续时提高止盈位

---

### 3. 回撤控制模块 (DrawdownController)

#### 回撤层级管理

| 回撤幅度 | 等级 | 响应措施 |
|----------|------|----------|
| 0-5% | 正常 | 正常交易 |
| 5-10% | 警告 | 降低仓位 20% |
| 10-15% | 危险 | 降低仓位 50% |
| >15% | 严重 | 降低仓位 75%，暂停新开仓 |

#### 日亏损限制

```
单日最大亏损：3%
- 达到 2%: 发出警告
- 达到 3%: 停止当日交易

防止单日重大失误导致不可控损失
```

#### 连续亏损限制

```
最大连续亏损次数：5 次
- 触发后：强制降仓 50%
- 统计窗口：10 个交易日

避免在不利市场环境下持续交易
```

#### 自动降仓机制

```python
deleveraging_thresholds = [0.05, 0.10, 0.15]  # 回撤阈值
deleveraging_ratios = [0.80, 0.50, 0.25]     # 对应仓位比例

# 回撤达到阈值时自动执行
if current_drawdown >= threshold:
    leverage_ratio = corresponding_ratio
```

#### 恢复机制

- **冷却期**: 降仓后至少 5 天
- **恢复条件**: 从低点反弹 5% 以上
- **渐进恢复**: 逐步恢复至正常仓位

---

### 4. 风险指标模块 (RiskMetricsCalculator)

#### VaR (Value at Risk)

**定义**: 在给定置信度下，最大可能损失

```
计算方法:
1. 历史法：直接取历史收益率分位数
2. 参数法：假设正态分布，VaR = μ - Z×σ
3. 蒙特卡洛：模拟 10000 次路径

默认参数:
- 置信度：95%
- 窗口期：252 天
- 最大 VaR 限额：5%
```

#### 夏普比率 (Sharpe Ratio)

```
夏普比率 = (组合年化收益 - 无风险利率) / 年化波动率

评估标准:
- Sharpe < 0: 亏损
- Sharpe 0-1: 一般
- Sharpe 1-2: 良好
- Sharpe > 2: 优秀

最低要求：1.0
```

#### 索提诺比率 (Sortino Ratio)

```
索提诺比率 = (组合年化收益 - 无风险利率) / 下行波动率

优势：只考虑下行风险，更适合评估不对称收益分布
```

#### Beta 暴露

```
Beta = Cov(Rp, Rm) / Var(Rm)

含义:
- Beta = 1: 与市场同步
- Beta > 1: 放大市场波动 (激进)
- Beta < 1: 缓冲市场波动 (保守)

最大限制：1.5
```

#### 行业/因子暴露

**行业暴露计算**:
```python
sector_exposure = Σ(持仓权重 × 行业归属)
最大行业暴露：40%
```

**因子暴露** (通过回归计算):
- 市场因子 (Market)
- 规模因子 (Size)
- 价值因子 (Value)
- 动量因子 (Momentum)
- 波动率因子 (Volatility)

#### 综合风险评分

```
风险评分 (0-100) = Σ(分项评分 × 权重)

分项权重:
- VaR: 30%
- 夏普比率：20%
- Beta: 20%
- 集中度：15%
- 回撤：15%

风险等级:
- 0-20: MINIMAL (极低风险)
- 20-40: LOW (低风险)
- 40-60: MEDIUM (中等风险)
- 60-80: HIGH (高风险)
- 80-100: CRITICAL (严重风险)
```

---

## 使用示例

### 初始化风险管理系统

```python
from src.risk import PositionManager, StopLossManager, DrawdownController, RiskMetricsCalculator

# 1. 仓位管理
position_config = PositionConfig(
    max_position_pct=0.20,      # 单标的最大 20%
    max_total_exposure=1.0,     # 总敞口 100%
    kelly_fraction=0.25         # 1/4 Kelly
)
position_mgr = PositionManager(position_config)

# 2. 止损管理
stop_config = StopLossConfig(
    fixed_stop_loss_pct=0.08,   # 8% 固定止损
    trailing_stop_pct=0.10,     # 10% 跟踪止损
    max_holding_days=30         # 30 天时间止损
)
stop_mgr = StopLossManager(stop_config)

# 3. 回撤控制
drawdown_config = DrawdownConfig(
    max_drawdown_pct=0.15,      # 最大回撤 15%
    max_daily_loss_pct=0.03,    # 日亏损 3%
    max_consecutive_losses=5    # 连续亏损 5 次
)
drawdown_ctrl = DrawdownController(drawdown_config)
drawdown_ctrl.initialize(1000000)  # 初始资金 100 万

# 4. 风险指标
metrics_config = RiskMetricsConfig(
    var_confidence_level=0.95,  # 95% VaR
    min_sharpe=1.0,             # 最低夏普 1.0
    max_beta=1.5                # 最大 Beta 1.5
)
metrics_calc = RiskMetricsCalculator(metrics_config)
```

### 交易前风险检查

```python
# 检查仓位限制
allowed, reason = position_mgr.check_position_limit(
    symbol="AAPL",
    proposed_weight=0.15,
    sector="Technology"
)

if not allowed:
    print(f"交易被拒绝：{reason}")
    return

# 计算 Kelly 最优仓位
kelly = position_mgr.calculate_kelly_fraction(
    win_rate=0.55,
    avg_win=0.12,
    avg_loss=0.06
)
optimal_position = min(kelly, 0.20)  # 不超过 20%

# 检查日亏损限制
daily_pnl = calculate_daily_pnl()
allowed, reason = drawdown_ctrl.check_daily_loss_limit(daily_pnl)

if not allowed:
    print(f"停止交易：{reason}")
    return
```

### 持仓监控

```python
# 更新价格并检查止损
trigger_info = stop_mgr.update_price(
    symbol="AAPL",
    current_price=175.50,
    current_date=datetime.now()
)

if trigger_info:
    execute_trade(
        symbol=trigger_info['symbol'],
        action='sell',
        reason=trigger_info['reason']
    )

# 更新组合价值和回撤
status = drawdown_ctrl.update_portfolio_value(
    current_value=950000,
    current_date=datetime.now()
)

if status['drawdown_level'] != 'normal':
    print(f"回撤警告：{status['drawdown']:.2%}")
    
# 获取允许仓位
base_size = calculate_base_position()
allowed_size = drawdown_ctrl.get_allowed_position_size(base_size)
```

### 风险报告

```python
# 添加收益率数据
metrics_calc.add_return(
    portfolio_return=0.012,
    benchmark_return=0.008,
    date=datetime.now()
)

# 获取完整风险报告
report = metrics_calc.get_risk_report(portfolio_value=1000000)

print(f"VaR (95%): {report['var_metrics']['var_1d_pct']:.2%}")
print(f"夏普比率：{report['sharpe_metrics']['sharpe_ratio']:.2f}")
print(f"Beta: {report['beta_metrics']['beta']:.2f}")
print(f"风险等级：{report['risk_score']['risk_level']}")
```

---

## 风险管理流程

### 交易前

```
1. 检查日亏损限额 → 超限则停止交易
2. 计算 Kelly 最优仓位
3. 检查仓位限制 (单标的/行业/总敞口)
4. 检查集中度风险
5. 设置止损止盈位
```

### 交易中

```
1. 实时监控价格
2. 触发止损自动执行
3. 跟踪止损动态调整
4. 时间止损到期提醒
```

### 交易后

```
1. 更新组合价值
2. 计算当日回撤
3. 检查回撤等级
4. 触发降仓机制 (如需要)
5. 更新风险指标
6. 生成风险报告
```

### 定期审查

```
每日:
- 日亏损检查
- 止损状态更新
- 回撤监控

每周:
- 风险指标计算
- 集中度分析
- 策略表现评估

每月:
- 全面风险审查
- 参数优化调整
- 压力测试
```

---

## 风险参数配置建议

### 保守型

```python
PositionConfig:
    max_position_pct: 0.10      # 单标的 10%
    kelly_fraction: 0.125       # 1/8 Kelly
    
StopLossConfig:
    fixed_stop_loss_pct: 0.05   # 5% 止损
    trailing_stop_pct: 0.08     # 8% 跟踪
    
DrawdownConfig:
    max_drawdown_pct: 0.10      # 最大回撤 10%
    max_daily_loss_pct: 0.02    # 日亏损 2%
```

### 平衡型 (默认)

```python
PositionConfig:
    max_position_pct: 0.20      # 单标的 20%
    kelly_fraction: 0.25        # 1/4 Kelly
    
StopLossConfig:
    fixed_stop_loss_pct: 0.08   # 8% 止损
    trailing_stop_pct: 0.10     # 10% 跟踪
    
DrawdownConfig:
    max_drawdown_pct: 0.15      # 最大回撤 15%
    max_daily_loss_pct: 0.03    # 日亏损 3%
```

### 激进型

```python
PositionConfig:
    max_position_pct: 0.30      # 单标的 30%
    kelly_fraction: 0.50        # 1/2 Kelly
    
StopLossConfig:
    fixed_stop_loss_pct: 0.12   # 12% 止损
    trailing_stop_pct: 0.15     # 15% 跟踪
    
DrawdownConfig:
    max_drawdown_pct: 0.25      # 最大回撤 25%
    max_daily_loss_pct: 0.05    # 日亏损 5%
```

---

## 应急响应机制

### 市场危机处理

```
触发条件:
- 单日市场跌幅 > 5%
- VIX 指数 > 40
- 组合单日亏损 > 5%

响应措施:
1. 立即降仓至 25%
2. 收紧所有止损至 5%
3. 暂停新开仓
4. 每日风险评估
```

### 系统故障处理

```
1. 止损失效:
   - 手动执行止损
   - 检查系统日志
   - 修复后验证

2. 数据中断:
   - 使用最后可用数据
   - 暂停新开仓
   - 保持现有止损

3. 执行失败:
   - 重试机制 (3 次)
   - 人工介入
   - 记录故障
```

---

## 监控与告警

### 告警级别

| 级别 | 条件 | 响应 |
|------|------|------|
| INFO | 正常波动 | 记录日志 |
| WARNING | 接近限制 | 通知提醒 |
| ERROR | 触及限制 | 自动执行 + 通知 |
| CRITICAL | 严重超限 | 紧急处理 + 人工介入 |

### 告警渠道

- 飞书消息通知
- 邮件告警
- 短信紧急通知 (CRITICAL 级别)

---

## 回测与验证

### 历史回测

使用历史数据验证风险参数:

```python
# 回测不同参数组合
param_grid = {
    'stop_loss_pct': [0.05, 0.08, 0.10],
    'max_drawdown': [0.10, 0.15, 0.20],
    'position_limit': [0.15, 0.20, 0.25]
}

# 评估指标
- 最大回撤
- 夏普比率
- 胜率
- 盈亏比
- 风险调整后收益
```

### 压力测试

```
测试场景:
1. 2008 金融危机 (-50% 市场)
2. 2020 疫情崩盘 (-30% 快速下跌)
3. 震荡市 (±20% 区间波动)
4. 黑天鹅 (单日 -10%)

通过标准:
- 最大回撤 < 配置限制
- 恢复时间 < 6 个月
- 无爆仓风险
```

---

## 总结

本风险管理系统通过四层防护体系，为 Q脑量化交易提供全方位风险保护:

1. **仓位管理** - 事前控制，确保不超限
2. **止损止盈** - 事中保护，限制单笔损失
3. **回撤控制** - 整体防护，防止重大亏损
4. **风险指标** - 量化监控，科学评估

核心理念：**宁可错过机会，不可承受不可控风险**

通过严格执行风险规则，Q脑能够在复杂多变的市场环境中保护资金安全，实现长期稳健收益。
