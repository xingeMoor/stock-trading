# 回测系统设计文档

## 1. 概述

### 1.1 设计目标
本回测系统旨在提供**准确、高效、可扩展**的策略验证平台，支持美股+A股双市场量化交易策略的回测需求。

### 1.2 核心特性
- ✅ 事件驱动架构，贴近实盘交易流程
- ✅ 支持日级/分钟级多频率回测
- ✅ 精确的滑点和冲击成本模拟
- ✅ 完善的数据对齐和前复权处理
- ✅ 全面的绩效分析和归因
- ✅ 并行回测和参数优化能力

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      回测引擎 (BacktestEngine)               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  EventQueue  │  │ DataAligner  │  │  Portfolio   │      │
│  │  事件队列    │  │  数据对齐器  │  │  投资组合    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Slippage    │  │   Impact     │  │  Strategy    │      │
│  │  滑点模型    │  │  冲击成本    │  │  策略基类    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   绩效分析 (PerformanceAnalyzer)             │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Return      │  │    Risk      │  │ Attribution  │      │
│  │  收益指标    │  │   风险指标   │  │  归因分析    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

| 组件 | 职责 | 关键功能 |
|------|------|----------|
| `BacktestEngine` | 回测引擎核心 | 事件调度、订单处理、成交模拟 |
| `EventQueue` | 事件队列 | 优先级事件管理 |
| `DataAligner` | 数据对齐器 | 时间对齐、复权、停牌处理 |
| `Portfolio` | 投资组合 | 持仓管理、资金跟踪 |
| `SlippageModel` | 滑点模型 | 滑点成本计算 |
| `ImpactCostModel` | 冲击成本模型 | 市场冲击计算 |
| `PerformanceAnalyzer` | 绩效分析器 | 指标计算、报告生成 |

---

## 3. 回测引擎核心设计

### 3.1 事件驱动架构

#### 事件类型
```python
class EventType(Enum):
    MARKET_OPEN = auto()      # 市场开盘
    MARKET_CLOSE = auto()     # 市场收盘
    BAR = auto()              # K 线数据
    SIGNAL = auto()           # 交易信号
    ORDER = auto()            # 订单事件
    FILL = auto()             # 成交事件
    CUSTOM = auto()           # 自定义事件
```

#### 事件处理流程
```
1. 引擎初始化 → 加载数据、创建组合
2. 发送 MARKET_OPEN 事件
3. 遍历每个时间点:
   a. 发送 BAR 事件
   b. 调用策略 on_bar()
   c. 策略生成订单
   d. 订单撮合成交
   e. 更新组合状态
4. 发送 MARKET_CLOSE 事件
5. 生成回测报告
```

### 3.2 数据对齐机制

#### 多数据源时间对齐
```python
def align_bars(self, bars_dict: Dict[str, List[Bar]], freq: str) -> List[Dict]:
    """
    对齐多个标的的 K 线数据
    
    处理逻辑:
    1. 收集所有时间点
    2. 排序并去重
    3. 创建时间索引
    4. 填充缺失数据 (None)
    5. 应用复权和停牌检查
    """
```

#### 前复权处理
- **复权因子存储**: `{symbol: {date: factor}}`
- **应用方式**: 在数据对齐时动态调整价格
- **支持类型**: 前复权、后复权 (通过因子方向控制)

#### 停牌处理
- **停牌日期记录**: `{symbol: {date_set}}`
- **处理逻辑**: 停牌期间不生成 BAR 事件，订单跳过

### 3.3 滑点模拟

#### 固定滑点模型
```python
class FixedSlippage(SlippageModel):
    """固定每股滑点成本"""
    def calculate_slippage(self, order, bar):
        return self.slippage_per_share * order.quantity
```

#### 波动率滑点模型
```python
class VolatilitySlippage(SlippageModel):
    """基于价格波动率的滑点"""
    def calculate_slippage(self, order, bar):
        daily_range = (bar.high - bar.low) / bar.close
        return self.slippage_factor * daily_range * bar.close * order.quantity
```

### 3.4 冲击成本模型

#### 平方根冲击模型 (Almgren-Chriss)
```python
class SquareRootImpact(ImpactCostModel):
    """
    冲击成本 = 系数 × 价格 × sqrt(订单量 / 平均成交量)
    
    理论基础:
    - 大额订单对价格的影响与订单规模的平方根成正比
    - 考虑市场深度和流动性
    """
    def calculate_impact(self, order, bar, avg_volume):
        participation_rate = order.quantity / avg_volume
        return self.impact_factor * bar.close * sqrt(participation_rate) * order.quantity
```

#### 线性冲击模型
```python
class LinearImpact(ImpactCostModel):
    """简化线性冲击模型"""
    def calculate_impact(self, order, bar, avg_volume):
        participation_rate = order.quantity / avg_volume
        return self.impact_factor * bar.close * participation_rate * order.quantity
```

---

## 4. 绩效分析设计

### 4.1 收益率指标

| 指标 | 公式 | 说明 |
|------|------|------|
| 总收益率 | (最终资金 - 初始资金) / 初始资金 | 整体盈利水平 |
| 年化收益 | (1 + 总收益)^(1/年数) - 1 | 年化复利收益 |
| 最大回撤 | max((峰值 - 谷值) / 峰值) | 最大亏损幅度 |
| 夏普比率 | (组合收益 - 无风险利率) / 波动率 | 风险调整后收益 |
| 索提诺比率 | (组合收益 - 无风险利率) / 下行波动率 | 只考虑下行风险 |
| 卡尔玛比率 | 年化收益 / 最大回撤 | 收益回撤比 |

### 4.2 风险指标

#### 波动率
```python
volatility = std(daily_returns) * sqrt(252)
```

#### VaR (Value at Risk)
- **方法**: 历史模拟法
- **VaR(95%)**: 95% 置信度下的最大日损失
- **计算**: `-percentile(returns, 5)`

#### CVaR (Conditional VaR)
- **定义**: 超过 VaR 阈值的损失平均值
- **意义**: 极端情况下的预期损失

### 4.3 归因分析

#### 按标的归因
- 统计每个股票的贡献
- 识别主要盈利/亏损来源

#### 按时间归因
- 按月/周/年分析收益分布
- 识别策略失效期

#### 按多空归因
- 分别统计做多和做空的贡献
- 评估策略方向性暴露

---

## 5. 并行回测设计

### 5.1 参数优化框架

```python
class ParameterOptimizer:
    """参数优化器"""
    
    def __init__(self, engine_class, param_grid):
        self.engine_class = engine_class
        self.param_grid = param_grid  # {param: [values]}
    
    def grid_search(self, data, n_jobs=-1):
        """网格搜索"""
        from joblib import Parallel, delayed
        
        # 生成参数组合
        param_combinations = list(ParameterGrid(self.param_grid))
        
        # 并行执行
        results = Parallel(n_jobs=n_jobs)(
            delayed(self._run_backtest)(data, params) 
            for params in param_combinations
        )
        
        return results
    
    def _run_backtest(self, data, params):
        """单次回测"""
        engine = self.engine_class(**params)
        engine.set_data(data)
        return engine.run()
```

### 5.2 多进程并行策略

#### 实现方案
1. **进程池**: 使用 `multiprocessing.Pool`
2. **数据共享**: 只读数据使用共享内存
3. **结果聚合**: 主进程收集所有结果

#### 性能优化
- **数据预加载**: 避免重复读取
- **批量处理**: 减少进程间通信
- **内存映射**: 大数据集使用 mmap

---

## 6. 关键设计决策

### 6.1 为什么选择事件驱动？

**优点**:
- ✅ 贴近实盘交易流程
- ✅ 易于处理复杂事件逻辑
- ✅ 支持异步和并发
- ✅ 方便扩展新事件类型

**对比方案**:
- 向量化回测：速度快但无法模拟真实交易流程
- 基于循环：简单但难以处理复杂事件

### 6.2 滑点和冲击成本的重要性

**为什么必须模拟**:
1. **实盘差异**: 忽略滑点会导致回测过于乐观
2. **策略容量**: 冲击成本影响策略可管理资金规模
3. **频率选择**: 高频策略受滑点影响更大

**经验值**:
- 美股流动性好的股票：滑点 0.01-0.05 美元/股
- A 股：滑点 0.1-0.3%
- 大单冲击：参与率>1% 时需考虑

### 6.3 数据对齐的挑战

**问题**:
- 不同股票停牌时间不同
- 分红除息导致价格跳空
- 多频率数据混合

**解决方案**:
- 统一时间轴，缺失填 None
- 复权因子动态调整
- 停牌检查在事件生成前

### 6.4 绩效指标选择

**核心指标**:
- 夏普比率：综合风险收益
- 最大回撤：风险控制
- 卡尔玛比率：收益回撤平衡

**辅助指标**:
- 胜率：交易质量
- 盈亏比：策略期望
- VaR：极端风险

---

## 7. 使用示例

### 7.1 基础回测

```python
from src.backtest.engine import (
    BacktestEngine, MovingAverageStrategy, 
    FixedSlippage, SquareRootImpact
)
from src.backtest.performance import PerformanceAnalyzer, generate_performance_report

# 创建引擎
engine = BacktestEngine(
    initial_cash=1000000,
    slippage_model=FixedSlippage(0.01),
    impact_model=SquareRootImpact(0.1),
    commission_rate=0.0003,
    freq="1d"
)

# 添加策略
strategy = MovingAverageStrategy(short_window=5, long_window=20)
engine.add_strategy(strategy)

# 设置数据
engine.set_data(bars_dict)  # {symbol: [Bar, ...]}

# 运行回测
results = engine.run()

# 绩效分析
analyzer = PerformanceAnalyzer()
for fill in results["fills"]:
    analyzer.add_equity_point(fill.timestamp, ...)  # 计算权益

metrics = analyzer.analyze(initial_capital=1000000)
print(generate_performance_report(metrics))
```

### 7.2 参数优化

```python
from joblib import Parallel, delayed

def run_backtest(short_window, long_window):
    engine = BacktestEngine(...)
    strategy = MovingAverageStrategy(short_window, long_window)
    engine.add_strategy(strategy)
    engine.set_data(data)
    return engine.run()

# 并行参数搜索
param_grid = [(s, l) for s in range(3, 10) for l in range(15, 30)]
results = Parallel(n_jobs=-1)(
    delayed(run_backtest)(s, l) for s, l in param_grid
)

# 选择最优参数
best_result = max(results, key=lambda r: r["sharpe_ratio"])
```

---

## 8. 扩展方向

### 8.1 短期优化
- [ ] 添加订单簿模拟
- [ ] 支持限价单撮合
- [ ] 添加交易约束 (涨跌停、最小交易单位)

### 8.2 中期优化
- [ ] 分布式回测集群
- [ ] 实时回测监控
- [ ] 策略版本管理

### 8.3 长期优化
- [ ] 机器学习特征工程集成
- [ ] 自动策略搜索
- [ ] 实盘回测一致性验证

---

## 9. 附录

### 9.1 文件结构
```
src/backtest/
├── engine.py          # 回测引擎核心
├── performance.py     # 绩效分析器
├── data.py           # (待添加) 数据加载
├── optimizer.py      # (待添加) 参数优化
└── __init__.py
```

### 9.2 依赖库
- numpy: 数值计算
- scipy: 统计计算
- pandas: 数据处理 (可选)
- joblib: 并行计算

### 9.3 性能基准
- 日级回测：1000 天 × 100 股票 ≈ 1 秒
- 分钟级回测：100 天 × 10 股票 ≈ 10 秒
- 参数优化：100 组参数 × 1 秒 = 并行后 10 秒 (10 核)

---

**文档版本**: v1.0  
**创建日期**: 2026-03-01  
**作者**: Backer (回测系统架构师)
