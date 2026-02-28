# 量化交易公司系统使用指南

**版本**: v3.0.0  
**更新时间**: 2026-02-27

---

## 🏢 系统架构

本系统模拟真实量化交易公司的完整组织架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    量化交易公司                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  【研究部门】                                                │
│  ├─ 基本面分析师 (Fundamental Analyst)                      │
│  ├─ 技术分析师 (Technical Analyst)                          │
│  └─ 舆情分析师 (Sentiment Analyst)                          │
│                                                             │
│  【风控部门】                                                │
│  └─ 风险管理师 (Risk Manager)                               │
│                                                             │
│  【策略部门】                                                │
│  └─ 策略师 (Strategist)                                     │
│                                                             │
│  【决策委员会】                                              │
│  └─ LLM 投资委员会 (Investment Committee)                   │
│                                                             │
│  【学习进化系统】                                            │
│  └─ 迭代学习系统 (Iterative Learning)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 使用流程

### 方式 1: 单次决策流程

```python
from src.quant_firm import QuantTradingFirm

# 创建公司
firm = QuantTradingFirm()

# 准备市场数据
market_data = {
    'technical_indicators': {
        'current_price': 175.0,
        'sma_20': 170.0,
        'sma_50': 165.0,
        'sma_200': 155.0,
        'rsi_14': 45.0,
        'macd': 2.5,
        'macd_signal': 1.8
    },
    'sentiment': {
        'composite_score': 0.25
    },
    'market_conditions': {
        'volatility': 0.025,
        'current_price': 175.0
    }
}

# 执行研究决策
decision = firm.research_and_decide('GOOGL', market_data)

# 输出决策
print(f"最终决策：{decision['final_decision']['final_action']}")
```

---

### 方式 2: LLM 委员会决策

```python
from src.llm_committee import llm_committee_decision_sync

# 收集各方报告
reports = {
    'FundamentalAnalyst': {...},
    'TechnicalAnalyst': {...},
    'SentimentAnalyst': {...},
    'RiskManager': {...},
    'Strategist': {...}
}

# LLM 决策
decision = llm_committee_decision_sync(
    symbol='GOOGL',
    reports=reports,
    backtest_history=[...],
    market_data={...}
)

print(f"LLM 决策：{decision['final_action']}")
```

---

### 方式 3: 多轮迭代学习

```python
from src.iterative_learning import IterativeLearningSystem
from strategies.optimized_v2_strategy import optimized_v2_strategy

# 创建学习系统
system = IterativeLearningSystem(
    symbols=['GOOGL', 'AAPL', 'MSFT'],
    start_date='2025-06-01',
    end_date='2026-02-27',
    strategy_func=optimized_v2_strategy,
    target_metrics={
        'min_total_return': 20,
        'max_drawdown': -15
    }
)

# 运行迭代
result = system.run_iterations(max_iterations=5)

# 输出学习结果
print(f"关键学习：{result['learnings']}")
```

---

## 🎯 完整工作流

### Step 1: 数据准备

```bash
# 获取市场数据
python3 main.py analyze GOOGL
```

### Step 2: 多角色分析

```python
from src.quant_firm import QuantTradingFirm

firm = QuantTradingFirm()
decision = firm.research_and_decide('GOOGL', market_data)
```

### Step 3: LLM 最终决策

```python
from src.llm_committee import build_committee_prompt, parse_committee_decision

# 构建提示词
prompt = build_committee_prompt('GOOGL', reports, backtest_history, market_data)

# 调用 LLM (使用你的 LLM 客户端)
response = call_llm_api(prompt)

# 解析决策
decision = parse_committee_decision(response)
```

### Step 4: 回测验证

```bash
# 回测决策
python3 main.py backtest GOOGL --start 2025-06-01 --strategy optimized_v2
```

### Step 5: 迭代学习

```python
from src.iterative_learning import IterativeLearningSystem

system = IterativeLearningSystem(...)
result = system.run_iterations(max_iterations=5)
```

### Step 6: 策略优化

根据学习结果调整策略参数，返回 Step 1 继续迭代。

---

## 📊 角色职责详解

### 1️⃣ 基本面分析师

**职责**: 分析公司财务数据、业务模式、竞争优势

**输出**:
- 评级 (BUY/HOLD/SELL)
- 置信度 (0-1)
- 分析理由

**待集成数据源**:
- 财务报表 API
- 行业分析数据
- 竞争对手对比

---

### 2️⃣ 技术分析师

**职责**: 分析价格走势、技术指标、图表形态

**输出**:
- 评级
- 趋势判断 (BULLISH/BEARISH/NEUTRAL)
- 动量判断 (OVERSOLD/OVERBOUGHT/NEUTRAL)
- 支撑位/阻力位

**使用指标**:
- SMA/EMA (趋势)
- RSI (超买超卖)
- MACD (动量)

---

### 3️⃣ 舆情分析师

**职责**: 分析新闻、社交媒体、分析师评级

**输出**:
- 评级
- 综合情绪评分 (-1 到 1)
- 情绪来源分解

**数据源**:
- Finviz 新闻
- Reddit 社交
- 分析师评级

---

### 4️⃣ 风险管理师

**职责**: 评估风险、设置仓位限制、止损建议

**输出**:
- 风险等级 (LOW/MEDIUM/HIGH)
- 建议仓位 (0-100%)
- 止损价
- 止盈价

**评估维度**:
- 波动率
- 最大回撤
- 流动性

---

### 5️⃣ 策略师

**职责**: 制定交易策略、参数优化、回测验证

**输出**:
- 策略建议 (BUY/SELL/HOLD)
- 推荐策略版本
- 参数配置
- 历史回测参考

**工作内容**:
- 综合各方意见
- 参考历史回测
- 提出策略调整

---

### 6️⃣ LLM 投资委员会

**职责**: 综合所有报告，做出最终投资决策

**输出**:
- 最终决策 (BUY/SELL/HOLD)
- 置信度
- 建议仓位
- 详细理由
- 风险提示
- 应对方案

**决策原则**:
1. 多方验证 (至少 2 个分析师支持)
2. 风险优先
3. 历史参考
4. 明确止损
5. 置信度门槛 (>0.6)

---

## 🔄 迭代学习流程

### 流程循环

```
回测 → 分析 → 假设 → 优化 → 验证 → 学习
  ↑                                      │
  └──────────────────────────────────────┘
```

### 每轮迭代输出

1. **回测结果**: 所有股票表现
2. **分析**: 平均收益、最佳/最差股票
3. **假设**: 优化方向建议
4. **学习**: 经验总结

### 停止条件

- 达到目标指标
- 达到最大迭代次数
- 收益不再提升

---

## 📁 文件结构

```
stock-trading/
├── src/
│   ├── quant_firm.py           # 量化公司 (多角色系统)
│   ├── llm_committee.py        # LLM 投资委员会
│   ├── iterative_learning.py   # 迭代学习系统
│   ├── backtest.py             # 回测引擎
│   ├── massive_api.py          # 数据获取
│   ├── sentiment_api.py        # 舆情分析
│   └── llm_decision.py         # LLM 决策
├── strategies/
│   ├── optimized_v2_strategy.py  # 优化策略 V2
│   ├── relaxed_strategy.py       # 宽松策略
│   └── ...
├── main.py                     # 命令行入口
└── docs/
    ├── QUANT_FIRM_GUIDE.md     # 本文档
    ├── P0_OPTIMIZATION_REPORT.md
    └── ROBUSTNESS_TEST_REPORT.md
```

---

## 🚀 快速开始

```bash
cd /Users/gexin/.openclaw/workspace/stock-trading

# 1. 测试量化公司系统
python3 src/quant_firm.py

# 2. 测试 LLM 委员会
python3 src/llm_committee.py

# 3. 测试迭代学习
python3 src/iterative_learning.py

# 4. 完整回测
python3 main.py backtest GOOGL --start 2025-06-01 --strategy optimized_v2

# 5. 多股票迭代
python3 main.py iterate GOOGL,AAPL,MSFT --start 2025-06-01 --end 2026-02-27
```

---

## 📈 下一步发展

### 短期 (本周)
- [ ] 集成真实财务数据 API
- [ ] 完善 LLM 决策提示词
- [ ] 添加更多技术指标

### 中期 (本月)
- [ ] 多策略框架
- [ ] 实时数据接入
- [ ] 自动化迭代优化

### 长期 (本季)
- [ ] 机器学习模型
- [ ] 实盘交易接口
- [ ] 风险监控系统

---

**文档版本**: v1.0  
**最后更新**: 2026-02-27  
**维护者**: 量化交易公司研发团队
