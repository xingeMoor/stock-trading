# 因子分析框架文档

## 概述

本框架为 Q脑量化交易系统提供完整的因子分析体系，包括技术因子计算、因子分析、有效性检验和因子合成等功能。

## 架构设计

```
src/factors/
├── __init__.py              # 包初始化
├── technical_factors.py     # 技术因子计算模块
└── factor_analyzer.py       # 因子分析器模块
```

## 因子列表

### 1. 技术指标因子 (TechnicalFactors)

#### 趋势类因子
| 因子名称 | 代码方法 | 说明 | 默认参数 |
|---------|---------|------|---------|
| SMA | `sma(period)` | 简单移动平均 | period=20 |
| EMA | `ema(period)` | 指数移动平均 | period=20 |
| MACD | `macd(fast, slow, signal)` | 移动平均收敛发散 | 12, 26, 9 |
| ADX | `adx(period)` | 平均趋向指标 | period=14 |

#### 动量类因子
| 因子名称 | 代码方法 | 说明 | 默认参数 |
|---------|---------|------|---------|
| RSI | `rsi(period)` | 相对强弱指标 | period=14 |
| Williams %R | `williams_r(period)` | 威廉指标 | period=14 |
| CCI | `cci(period)` | 商品通道指标 | period=20 |

#### 波动类因子
| 因子名称 | 代码方法 | 说明 | 默认参数 |
|---------|---------|------|---------|
| Bollinger Bands | `bollinger_bands(period, std_dev)` | 布林带 | 20, 2.0 |
| ATR | `atr(period)` | 平均真实波幅 | period=14 |

#### 成交量类因子
| 因子名称 | 代码方法 | 说明 | 默认参数 |
|---------|---------|------|---------|
| OBV | `obv()` | 能量潮指标 | - |
| VWAP | `vwap()` | 成交量加权平均价 | - |
| Volume Ratio | `volume_ratio(period)` | 成交量比率 | period=20 |

### 2. 量价因子 (待扩展)

在 `technical_factors.py` 基础上可扩展:

- **价格形态识别**: 头肩顶、双底、三角形等形态检测
- **成交量异常检测**: 成交量突增/突降识别
- **资金流向分析**: 大单净流入、主力动向等

### 3. 多因子模型功能 (FactorAnalyzer)

| 功能 | 方法 | 说明 |
|-----|------|------|
| 因子标准化 | `standardize(method)` | zscore/rank/minmax |
| 因子去极值 | `winsorize(limits)` | 分位数去极值 |
| 因子中性化 | `neutralize(benchmark)` | 去除市场影响 |
| 相关性分析 | `correlation_matrix(method)` | Pearson/Spearman/Kendall |
| 高相关因子对 | `high_correlation_pairs(threshold)` | 识别冗余因子 |
| PCA 分析 | `pca_analysis(n_components)` | 主成分分析 |
| IC 计算 | `calculate_ic(factor_name)` | 单因子 IC |
| 批量 IC | `calculate_all_ic()` | 所有因子 IC |
| IC 统计 | `ic_statistics()` | IC 均值/IR/T 统计等 |
| IC 衰减 | `ic_decay(factor_name)` | 不同滞后期 IC |
| 等权合成 | `equal_weight_synthesis()` | 等权因子合成 |
| IC 加权合成 | `ic_weight_synthesis()` | 按 IC_IR 加权 |
| PCA 合成 | `pca_synthesis()` | 主成分合成 |
| 因子筛选 | `select_factors_by_ic()` | 按 IC 筛选 |
| 低相关筛选 | `select_factors_by_low_correlation()` | 去冗余 |

## 使用示例

### 示例 1: 计算技术因子

```python
import pandas as pd
import numpy as np
from src.factors import TechnicalFactors

# 准备 OHLCV 数据
df = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
}, index=pd.date_range('2024-01-01', periods=100))

# 创建技术因子计算器
tf = TechnicalFactors(df)

# 计算单个因子
rsi = tf.rsi(period=14)
macd = tf.macd(fast=12, slow=26, signal=9)

# 计算所有因子
all_factors = tf.calculate_all_factors()
print(all_factors.tail())
```

### 示例 2: 因子有效性分析

```python
from src.factors import FactorAnalyzer

# 准备因子数据和收益率
factors_df = all_factors.dropna()
forward_returns = df['close'].pct_change().shift(-1)  # 次日收益率

# 创建因子分析器
analyzer = FactorAnalyzer(factors_df, forward_returns)

# 标准化处理
standardized = analyzer.standardize(method='zscore')

# 相关性分析
corr_matrix = analyzer.correlation_matrix(method='pearson')
high_corr = analyzer.high_correlation_pairs(threshold=0.7)
print("高相关性因子对:", high_corr)

# IC 分析
ic_df = analyzer.calculate_all_ic(method='spearman')
ic_stats = analyzer.ic_statistics(ic_df)
print("因子 IC 统计:")
print(ic_stats[['ic_mean', 'ic_ir', 'ic_positive_ratio']])

# 筛选有效因子
valid_factors = analyzer.select_factors_by_ic(min_ic=0.02, min_ir=0.5)
print("有效因子:", valid_factors)
```

### 示例 3: 因子合成

```python
# 等权合成
synthetic_equal = analyzer.equal_weight_synthesis()

# IC 加权合成
synthetic_ic = analyzer.ic_weight_synthesis()

# PCA 合成
synthetic_pca = analyzer.pca_synthesis(n_components=1)

# 查看合成因子
print("等权合成因子:")
print(synthetic_equal.tail())
```

### 示例 4: 完整工作流

```python
# 1. 数据准备
price_data = load_price_data('AAPL')  # 加载价格数据
tf = TechnicalFactors(price_data)

# 2. 计算技术因子
factors = tf.calculate_all_factors()

# 3. 数据预处理
analyzer = FactorAnalyzer(
    factors.dropna(), 
    forward_returns=price_data['close'].pct_change().shift(-1)
)

# 4. 标准化和去极值
factors_clean = analyzer.winsorize(limits=(0.01, 0.99))
factors_norm = analyzer.standardize(method='zscore')

# 5. 因子分析
analyzer.factors_df = factors_norm
ic_stats = analyzer.ic_statistics()

# 6. 因子筛选
valid_factors = analyzer.select_factors_by_ic(min_ic=0.02, min_ir=0.5)
low_corr_factors = analyzer.select_factors_by_low_correlation(threshold=0.5)

# 7. 因子合成
final_factors = list(set(valid_factors) & set(low_corr_factors))
synthetic_factor = analyzer.equal_weight_synthesis(factor_names=final_factors)

# 8. 生成报告
report = analyzer.generate_factor_report()
print(report)
```

## 因子评价标准

### IC 指标解读

| 指标 | 优秀 | 良好 | 可用 |
|-----|------|------|------|
| IC 均值 | > 0.05 | 0.02-0.05 | 0.01-0.02 |
| IC_IR | > 1.0 | 0.5-1.0 | 0.3-0.5 |
| 正 IC 比例 | > 60% | 55-60% | 50-55% |
| T 统计量 | > 2.5 | 2.0-2.5 | 1.5-2.0 |

### 因子筛选建议

1. **IC 门槛**: IC 均值 > 0.02, IC_IR > 0.5
2. **相关性门槛**: 因子间相关性 < 0.7
3. **稳定性**: 滚动 IC 标准差较小
4. **经济意义**: 因子逻辑清晰，有经济学解释

## 扩展开发

### 添加新因子

在 `technical_factors.py` 中添加新方法:

```python
def new_factor(self, param1=10, param2=20) -> pd.Series:
    """
    新因子计算
    
    Args:
        param1: 参数 1 说明
        param2: 参数 2 说明
        
    Returns:
        因子序列
    """
    # 因子计算逻辑
    factor = ...
    return factor
```

### 添加新分析方法

在 `factor_analyzer.py` 中添加新方法:

```python
def new_analysis(self, **kwargs) -> ResultType:
    """
    新分析方法
    
    Args:
        **kwargs: 参数
        
    Returns:
        分析结果
    """
    # 分析逻辑
    result = ...
    return result
```

## 注意事项

1. **数据质量**: 确保输入数据无缺失、无异常值
2. **前视偏差**: 计算因子时避免使用未来数据
3. **过拟合风险**: 因子数量不宜过多，注意样本外验证
4. **交易成本**: 实盘时需考虑换手率和交易成本
5. **市场状态**: 因子有效性可能随市场状态变化

## 依赖库

```python
pip install pandas numpy scipy scikit-learn
```

## 版本信息

- **版本**: 1.0.0
- **创建日期**: 2026-03-01
- **作者**: Q脑量化团队
- **维护**: Factor 因子分析师
