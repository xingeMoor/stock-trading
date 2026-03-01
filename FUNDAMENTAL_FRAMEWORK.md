# 基本面分析框架 (Fundamental Analysis Framework)

> Q 脑量化交易系统 - 基本面分析体系

## 📋 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [模块详解](#模块详解)
- [数据源规划](#数据源规划)
- [使用指南](#使用指南)
- [扩展计划](#扩展计划)

---

## 概述

本框架为 Q 脑量化交易系统提供完整的基本面分析能力，覆盖财务分析、估值建模、行业对比和财报跟踪四大核心领域。

### 核心目标

1. **选股支持** - 通过多维度财务指标筛选优质公司
2. **估值定价** - 运用多种估值模型确定合理价值区间
3. **风险评估** - 识别财务风险和竞争劣势
4. **事件跟踪** - 监控财报、分红、激励等重要事件

### 设计理念

```
┌─────────────────────────────────────────────────────────────┐
│                    Q 脑基本面分析体系                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  财务分析    │  │  估值模型    │  │  行业对比    │       │
│  │  Analyzer    │  │  Valuation   │  │  Comparison  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐                                           │
│  │  财报跟踪    │                                           │
│  │  Tracker     │                                           │
│  └──────────────┘                                           │
├─────────────────────────────────────────────────────────────┤
│                      数据源层                                 │
│   Yahoo Finance │ Alpha Vantage │ 聚宽 │ Wind │ 同花顺        │
└─────────────────────────────────────────────────────────────┘
```

---

## 架构设计

### 模块结构

```
src/fundamental/
├── financial_analyzer.py    # 财务分析模块
├── valuation_models.py      # 估值模型模块
├── industry_compare.py      # 行业对比模块
├── earnings_tracker.py      # 财报跟踪模块
└── __init__.py             # 模块导出
```

### 类关系图

```
FinancialAnalyzer
├── FinancialStatement (数据类)
├── calculate_liquidity_ratios()
├── calculate_profitability_ratios()
├── calculate_leverage_ratios()
├── calculate_efficiency_ratios()
├── dupont_analysis()
├── trend_analysis()
└── financial_health_score()

ValuationModels
├── ValuationInput (数据类)
├── dcf_model()
├── pe_valuation()
├── pb_valuation()
├── ps_valuation()
├── ev_ebitda_valuation()
├── peg_valuation()
└── comprehensive_valuation()

IndustryComparator
├── CompanyMetrics (数据类)
├── IndustryMetrics (数据类)
├── compare_to_industry()
├── find_competitors()
├── industry_ranking()
└── evaluate_moat()

EarningsTracker
├── EarningsReport (数据类)
├── EarningsPreview (数据类)
├── DividendInfo (数据类)
├── StockIncentive (数据类)
├── get_earnings_calendar()
├── analyze_earnings_surprise()
├── analyze_dividend_policy()
└── earnings_quality_score()
```

---

## 模块详解

### 1. 财务分析模块 (financial_analyzer.py)

#### 功能清单

| 功能类别 | 具体指标 |
|---------|---------|
| **流动性比率** | 流动比率、速动比率、现金比率 |
| **盈利能力** | 毛利率、营业利润率、净利率、ROE、ROA |
| **杠杆比率** | 资产负债率、产权比率、权益乘数 |
| **效率比率** | 总资产周转率、存货周转率、应收账款周转率 |
| **现金流比率** | 经营现金流比率、自由现金流收益率 |
| **杜邦分析** | 三因素/五因素 ROE 分解 |
| **趋势分析** | CAGR、平均增长率、趋势判断 |
| **健康评分** | 综合财务健康度评分 (0-100) |

#### 核心 API

```python
from src.fundamental import FinancialAnalyzer, FinancialStatement

# 初始化
analyzer = FinancialAnalyzer()

# 添加财报数据
statement = FinancialStatement(
    symbol='AAPL',
    report_date=datetime(2024, 12, 31),
    report_type='annual',
    revenue=385000000000,
    net_income=97000000000,
    total_assets=350000000000,
    total_equity=60000000000,
    # ... 更多字段
)
analyzer.add_statement(statement)

# 获取所有比率
ratios = analyzer.get_all_ratios(statement)
# 输出: {
#   'liquidity': {'current_ratio': 1.07, ...},
#   'profitability': {'roe': 161.67, ...},
#   ...
# }

# 杜邦分析
dupont = analyzer.dupont_analysis(statement)
# 输出: {'roe': 161.67, 'net_margin': 25.19, 'asset_turnover': 1.1, ...}

# 财务健康评分
health = analyzer.financial_health_score(statement)
# 输出: {'total_score': 75.5, 'rating': 'AA', ...}
```

#### 财务健康评分标准

| 评分 | 评级 | 说明 |
|-----|------|------|
| 85-100 | AAA | 财务极度健康 |
| 75-84 | AA | 财务很健康 |
| 65-74 | A | 财务健康 |
| 55-64 | BBB | 财务良好 |
| 45-54 | BB | 财务一般 |
| 35-44 | B | 财务较弱 |
| <35 | C | 财务风险高 |

---

### 2. 估值模型模块 (valuation_models.py)

#### 估值方法矩阵

| 方法 | 适用场景 | 核心输入 | 输出 |
|-----|---------|---------|------|
| **DCF** | 所有公司 | FCF、增长率、WACC | 内在价值、安全边际 |
| **PE** | 盈利稳定公司 | 净利润、行业 PE | 合理市值 |
| **PB** | 重资产行业 | 净资产、行业 PB | 合理市值 |
| **PS** | 高增长未盈利 | 营收、行业 PS | 合理市值 |
| **EV/EBITDA** | 资本密集型 | EBITDA、行业倍数 | 企业价值 |
| **PEG** | 成长股 | PE、增长率 | 估值合理性 |

#### 核心 API

```python
from src.fundamental import ValuationModels, ValuationInput

# 初始化
valuator = ValuationModels()

# 创建估值输入
input_data = ValuationInput(
    symbol='AAPL',
    current_price=175.0,
    shares_outstanding=15500000000,
    market_cap=2712500000000,
    free_cash_flow=100000000000,
    revenue=385000000000,
    net_income=97000000000,
    ebitda=125000000000,
    total_equity=60000000000,
    total_debt=110000000000,
    cash_and_equivalents=50000000000,
    fcf_growth_rate=0.08,
    terminal_growth_rate=0.02,
    beta=1.2,
    risk_free_rate=0.04
)

# DCF 估值
dcf_result = valuator.dcf_model(input_data)
# 输出: {
#   'wacc': 9.2,
#   'intrinsic_value_per_share': 195.50,
#   'margin_of_safety': 11.71,
#   'recommendation': 'BUY'
# }

# 相对估值
pe_result = valuator.pe_valuation(input_data, industry_pe=28.0)
ev_result = valuator.ev_ebitda_valuation(input_data, industry_ev_ebitda=22.0)

# 综合估值
industry_comps = {'pe': 28.0, 'pb': 45.0, 'ps': 7.0, 'ev_ebitda': 22.0}
comprehensive = valuator.comprehensive_valuation(input_data, industry_comps)
# 输出: {
#   'dcf': {...},
#   'pe_valuation': {...},
#   'consensus': {'target_price': 192.30, 'upside': 9.89}
# }
```

#### 投资建议规则

| 安全边际 | 建议 |
|---------|------|
| ≥30% | STRONG_BUY (强烈买入) |
| 15-30% | BUY (买入) |
| 0-15% | HOLD (持有) |
| -15-0% | REDUCE (减持) |
| <-15% | SELL (卖出) |

---

### 3. 行业对比模块 (industry_compare.py)

#### 分析维度

```
行业对比分析
├── 行业均值对比
│   ├── 估值指标 (PE/PB/PS/EV/EBITDA)
│   ├── 盈利能力 (ROE/ROA/毛利率/净利率)
│   └── 财务健康 (负债率/流动比率)
├── 竞争对手分析
│   ├── 市值对比
│   ├── 指标对比矩阵
│   └── 竞争定位
├── 行业排名
│   ├── 单指标排名
│   └── 综合排名
└── 护城河评估
    ├── 盈利能力护城河
    ├── 利润率护城河
    ├── 增长护城河
    ├── 财务健康护城河
    └── 估值护城河
```

#### 核心 API

```python
from src.fundamental import IndustryComparator, CompanyMetrics

# 初始化
comparator = IndustryComparator()

# 添加公司数据
company = CompanyMetrics(
    symbol='AAPL',
    name='Apple',
    sector='Technology',
    industry='Consumer Electronics',
    market_cap=2800000000000,
    pe_ratio=28,
    pb_ratio=45,
    roe=150,
    gross_margin=44,
    net_margin=25,
    revenue_growth=0.08,
    debt_to_equity=1.8,
    # ... 更多字段
)
comparator.add_company(company)

# 行业对比
comparison = comparator.compare_to_industry('AAPL')
# 输出: {
#   'metrics': {
#     'valuation': {'pe': {'company': 28, 'industry_avg': 25, 'vs_industry': 12.0}},
#     'profitability': {'roe': {'company': 150, 'industry_avg': 80, 'vs_industry': 70}},
#     ...
#   }
# }

# 护城河评估
moat = comparator.evaluate_moat('AAPL')
# 输出: {
#   'total_score': 75,
#   'moat_rating': 'Narrow',
#   'description': '窄护城河，有一定竞争优势',
#   'dimensions': {
#     'profitability': {'score': 25, 'reason': 'ROE >= 20%, 卓越盈利能力'},
#     ...
#   }
# }

# 行业排名
rankings = comparator.industry_ranking('Technology', metric='roe', top_n=10)
```

#### 护城河评级标准

| 总分 | 评级 | 说明 |
|-----|------|------|
| ≥80 | Wide | 宽护城河，竞争优势显著 |
| 60-79 | Narrow | 窄护城河，有一定竞争优势 |
| 40-59 | None | 无明显护城河 |
| <40 | Weak | 竞争地位薄弱 |

---

### 4. 财报跟踪模块 (earnings_tracker.py)

#### 跟踪事件类型

| 事件类型 | 说明 | 优先级 |
|---------|------|--------|
| 财报发布 | 季报/年报发布 | 高 |
| 业绩预告 | 业绩预增/预减公告 | 高 |
| 分红派息 | 现金分红/送股/配股 | 中 |
| 股权激励 | 员工持股/期权计划 | 中 |
| 业绩说明会 | 管理层交流会议 | 中 |

#### 核心 API

```python
from src.fundamental import EarningsTracker, EarningsReport, ReportType

# 初始化
tracker = EarningsTracker()
tracker.add_to_watchlist(['AAPL', 'MSFT', 'GOOGL'])

# 添加财报
report = EarningsReport(
    symbol='AAPL',
    report_date=datetime(2024, 12, 31),
    report_type=ReportType.Q1,
    fiscal_year=2024,
    fiscal_period='Q1 2024',
    revenue=120000000000,
    revenue_yoy=0.08,
    net_income=35000000000,
    eps=2.15,
    eps_yoy=0.12,
    estimated_revenue=118000000000,
    estimated_eps=2.10
)
tracker.add_earnings_report(report)

# 超预期分析
surprise = tracker.analyze_earnings_surprise('AAPL')
# 输出: {
#   'eps_beat_rate': 75.0,
#   'avg_eps_surprise': 3.5,
#   'surprises': [...]
# }

# 分红分析
dividend = tracker.analyze_dividend_policy('AAPL')
# 输出: {
#   'avg_dividend_yield': 0.55,
#   'dividend_growth_rate': 5.2,
#   'consecutive_years': 10,
#   'dividend_aristocrat': True
# }

# 财报质量评分
quality = tracker.earnings_quality_score('AAPL')
# 输出: {
#   'total_score': 82,
#   'rating': 'A',
#   'factors': {'surprise': 30, 'trend': 25, ...}
# }

# 财报日历
calendar = tracker.get_earnings_calendar(
    start_date=datetime.now(),
    end_date=datetime.now() + timedelta(days=30)
)

# 事件提醒
alerts = tracker.get_earnings_alerts()
```

#### 财报质量评分标准

| 总分 | 评级 | 说明 |
|-----|------|------|
| 85-100 | A+ | 财报质量极佳 |
| 75-84 | A | 财报质量优秀 |
| 65-74 | B+ | 财报质量良好 |
| 55-64 | B | 财报质量一般 |
| 45-54 | C | 财报质量较弱 |
| <45 | D | 财报质量差 |

---

## 数据源规划

### 推荐数据源

#### 美股数据

| 数据源 | 类型 | 免费额度 | 适用场景 |
|-------|------|---------|---------|
| **Yahoo Finance** | API/爬虫 | 免费 | 基础行情、财报 |
| **Alpha Vantage** | API | 5 次/分钟 | 财务指标、估值 |
| **IEX Cloud** | API | 付费 | 专业财务数据 |
| **Finnhub** | API | 60 次/分钟 | 实时行情、财报 |
| **SEC EDGAR** | 官方 | 免费 | 原始财报文件 |

#### A 股数据

| 数据源 | 类型 | 免费额度 | 适用场景 |
|-------|------|---------|---------|
| **聚宽 (JoinQuant)** | API | 免费 | 全面 A 股数据 |
| **Tushare** | API | 积分制 | 财务指标、行情 |
| **AkShare** | 爬虫 | 免费 | 多源数据聚合 |
| **Wind** | 终端 | 付费 | 专业机构数据 |
| **同花顺 iFinD** | 终端 | 付费 | 专业机构数据 |

### 数据获取策略

```python
# 数据源优先级配置
DATA_SOURCES = {
    'us_stocks': {
        'primary': 'yahoo_finance',
        'fallback': ['alpha_vantage', 'finnhub'],
        'official': 'sec_edgar'
    },
    'cn_stocks': {
        'primary': 'joinquant',
        'fallback': ['tushare', 'akshare'],
        'official': 'wind'
    }
}

# 数据更新频率
UPDATE_FREQUENCY = {
    'price': 'realtime',      # 实时
    'financials': 'quarterly', # 季度
    'estimates': 'daily',      # 每日
    'dividends': 'event',      # 事件驱动
    'insider': 'weekly'        # 每周
}
```

### 数据缓存策略

```
数据缓存架构
├── Redis (热数据)
│   ├── 实时行情 (TTL: 1 分钟)
│   ├── 估值指标 (TTL: 1 小时)
│   └── 财报日历 (TTL: 1 天)
├── PostgreSQL (冷数据)
│   ├── 历史财报
│   ├── 历史估值
│   └── 行业数据
└── 本地缓存 (SQLite)
    ├── 用户自选股
    └── 分析结果
```

---

## 使用指南

### 快速开始

```python
from src.fundamental import (
    FinancialAnalyzer, FinancialStatement,
    ValuationModels, ValuationInput,
    IndustryComparator, CompanyMetrics,
    EarningsTracker, EarningsReport
)

# 1. 财务分析
analyzer = FinancialAnalyzer()
statement = FinancialStatement(symbol='AAPL', ...)
analyzer.add_statement(statement)
ratios = analyzer.get_all_ratios(statement)
health_score = analyzer.financial_health_score(statement)

# 2. 估值建模
valuator = ValuationModels()
input_data = ValuationInput(symbol='AAPL', ...)
dcf_value = valuator.dcf_model(input_data)
comprehensive = valuator.comprehensive_valuation(input_data)

# 3. 行业对比
comparator = IndustryComparator()
comparator.add_company(CompanyMetrics(...))
industry_report = comparator.generate_industry_report('Technology')
moat = comparator.evaluate_moat('AAPL')

# 4. 财报跟踪
tracker = EarningsTracker()
tracker.add_earnings_report(EarningsReport(...))
quality_score = tracker.earnings_quality_score('AAPL')
alerts = tracker.get_earnings_alerts()
```

### 选股流程示例

```python
def screen_stocks(universe: List[str]) -> List[Dict]:
    """基本面选股流程"""
    results = []
    
    for symbol in universe:
        # 1. 获取财务数据
        statement = get_financial_statement(symbol)
        analyzer = FinancialAnalyzer()
        analyzer.add_statement(statement)
        
        # 2. 财务健康筛选
        health = analyzer.financial_health_score(statement)
        if health['total_score'] < 60:
            continue
        
        # 3. 估值分析
        input_data = create_valuation_input(symbol)
        valuator = ValuationModels()
        valuation = valuator.dcf_model(input_data)
        
        if valuation['margin_of_safety'] < 15:
            continue
        
        # 4. 行业对比
        comparator = IndustryComparator()
        moat = comparator.evaluate_moat(symbol)
        
        if moat['total_score'] < 60:
            continue
        
        # 5. 财报质量
        tracker = EarningsTracker()
        quality = tracker.earnings_quality_score(symbol)
        
        if quality['total_score'] < 65:
            continue
        
        # 通过筛选
        results.append({
            'symbol': symbol,
            'health_score': health['total_score'],
            'valuation_upside': valuation['margin_of_safety'],
            'moat_score': moat['total_score'],
            'quality_score': quality['total_score'],
            'composite_score': (
                health['total_score'] * 0.25 +
                valuation['margin_of_safety'] * 0.25 +
                moat['total_score'] * 0.25 +
                quality['total_score'] * 0.25
            )
        })
    
    # 按综合评分排序
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    return results
```

---

## 扩展计划

### 短期 (1-3 个月)

- [ ] 接入真实数据源 (Yahoo Finance, 聚宽)
- [ ] 实现数据缓存层
- [ ] 添加批量分析功能
- [ ] 完善异常处理
- [ ] 添加单元测试

### 中期 (3-6 个月)

- [ ] 集成到 Q 脑主系统
- [ ] 添加可视化报表
- [ ] 实现自动选股策略
- [ ] 添加分析师预期数据
- [ ] 支持多市场 (美股/A 股/港股)

### 长期 (6-12 个月)

- [ ] AI 辅助财务分析
- [ ] 自然语言财报摘要
- [ ] 风险预警系统
- [ ] 机构持仓跟踪
- [ ] ESG 评分集成

---

## 附录

### 关键财务指标公式

```
流动性比率:
  流动比率 = 流动资产 / 流动负债
  速动比率 = (流动资产 - 存货) / 流动负债
  现金比率 = 货币资金 / 流动负债

盈利能力:
  毛利率 = 毛利润 / 营业收入
  营业利润率 = 营业利润 / 营业收入
  净利率 = 净利润 / 营业收入
  ROE = 净利润 / 股东权益
  ROA = 净利润 / 总资产

杠杆比率:
  资产负债率 = 总负债 / 总资产
  产权比率 = 总负债 / 股东权益
  权益乘数 = 总资产 / 股东权益

效率比率:
  总资产周转率 = 营业收入 / 总资产
  存货周转率 = 营业成本 / 平均存货
  应收账款周转率 = 营业收入 / 平均应收账款

杜邦分析:
  ROE = 净利率 × 总资产周转率 × 权益乘数

估值指标:
  PE = 市值 / 净利润
  PB = 市值 / 净资产
  PS = 市值 / 营业收入
  EV/EBITDA = 企业价值 / 息税折旧摊销前利润
  PEG = PE / (净利润增长率 × 100)
```

### 版本历史

| 版本 | 日期 | 更新内容 |
|-----|------|---------|
| 1.0.0 | 2026-03-01 | 初始版本，四大核心模块完成 |

---

**文档维护**: Q 脑开发团队  
**最后更新**: 2026-03-01
