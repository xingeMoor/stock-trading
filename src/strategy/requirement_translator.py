#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
需求翻译器 (Requirement Translator)
将金融策略业务需求转化为技术实现规格
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import json
from datetime import datetime


class StrategyType(Enum):
    """策略类型枚举"""
    TREND_FOLLOWING = "trend_following"  # 趋势跟踪
    MEAN_REVERSION = "mean_reversion"  # 均值回归
    ARBITRAGE = "arbitrage"  # 套利
    MARKET_MAKING = "market_making"  # 做市
    FACTOR_INVESTING = "factor_investing"  # 因子投资
    OTHER = "other"  # 其他


class MarketType(Enum):
    """市场类型"""
    US_STOCK = "us_stock"  # 美股
    A_SHARE = "a_share"  # A 股
    HK_STOCK = "hk_stock"  # 港股
    FUTURES = "futures"  # 期货
    CRYPTO = "crypto"  # 加密货币


class FrequencyType(Enum):
    """交易频率"""
    HIGH_FREQUENCY = "high_frequency"  # 高频 (<1 分钟)
    INTRADAY = "intraday"  # 日内 (分钟级)
    DAILY = "daily"  # 日线
    WEEKLY = "weekly"  # 周线
    MONTHLY = "monthly"  # 月线


@dataclass
class BusinessRequirement:
    """业务需求原始描述"""
    strategy_name: str
    strategy_description: str
    expected_return: Optional[float]  # 期望年化收益率
    max_drawdown: Optional[float]  # 最大可接受回撤
    trading_frequency: str
    target_market: str
    capital_requirement: Optional[float]  # 资金需求
    risk_tolerance: str  # low/medium/high
    special_requirements: List[str] = field(default_factory=list)


@dataclass
class TechnicalSpecification:
    """技术规格说明"""
    strategy_id: str
    strategy_type: StrategyType
    market_type: MarketType
    frequency_type: FrequencyType
    data_requirements: Dict[str, Any]
    indicator_requirements: List[str]
    execution_requirements: Dict[str, Any]
    risk_controls: List[str]
    estimated_complexity: str  # low/medium/high
    estimated_development_days: int
    dependencies: List[str]
    technical_risks: List[str]


class RequirementTranslator:
    """需求翻译器核心类"""
    
    def __init__(self):
        self.strategy_type_mapping = {
            "趋势": StrategyType.TREND_FOLLOWING,
            "trend": StrategyType.TREND_FOLLOWING,
            "均值回归": StrategyType.MEAN_REVERSION,
            "mean reversion": StrategyType.MEAN_REVERSION,
            "套利": StrategyType.ARBITRAGE,
            "arbitrage": StrategyType.ARBITRAGE,
            "做市": StrategyType.MARKET_MAKING,
            "market making": StrategyType.MARKET_MAKING,
            "因子": StrategyType.FACTOR_INVESTING,
            "factor": StrategyType.FACTOR_INVESTING,
        }
        
        self.market_mapping = {
            "美股": MarketType.US_STOCK,
            "us": MarketType.US_STOCK,
            "usa": MarketType.US_STOCK,
            "A 股": MarketType.A_SHARE,
            "a 股": MarketType.A_SHARE,
            "china": MarketType.A_SHARE,
            "港股": MarketType.HK_STOCK,
            "hk": MarketType.HK_STOCK,
            "期货": MarketType.FUTURES,
            "futures": MarketType.FUTURES,
            "crypto": MarketType.CRYPTO,
            "币": MarketType.CRYPTO,
        }
        
        self.frequency_mapping = {
            "高频": FrequencyType.HIGH_FREQUENCY,
            "high": FrequencyType.HIGH_FREQUENCY,
            "hft": FrequencyType.HIGH_FREQUENCY,
            "日内": FrequencyType.INTRADAY,
            "intraday": FrequencyType.INTRADAY,
            "分钟": FrequencyType.INTRADAY,
            "minute": FrequencyType.INTRADAY,
            "日线": FrequencyType.DAILY,
            "daily": FrequencyType.DAILY,
            "日": FrequencyType.DAILY,
            "周线": FrequencyType.WEEKLY,
            "weekly": FrequencyType.WEEKLY,
            "周": FrequencyType.WEEKLY,
            "月线": FrequencyType.MONTHLY,
            "monthly": FrequencyType.MONTHLY,
            "月": FrequencyType.MONTHLY,
        }
    
    def translate(self, business_req: BusinessRequirement) -> TechnicalSpecification:
        """
        将业务需求转化为技术规格
        
        Args:
            business_req: 业务需求对象
            
        Returns:
            TechnicalSpecification: 技术规格对象
        """
        # 策略类型识别
        strategy_type = self._identify_strategy_type(business_req.strategy_description)
        
        # 市场类型识别
        market_type = self._identify_market_type(business_req.target_market)
        
        # 频率类型识别
        frequency_type = self._identify_frequency_type(business_req.trading_frequency)
        
        # 数据需求分析
        data_requirements = self._analyze_data_requirements(
            strategy_type, market_type, frequency_type
        )
        
        # 指标需求分析
        indicator_requirements = self._analyze_indicator_requirements(
            strategy_type, business_req.strategy_description
        )
        
        # 执行需求分析
        execution_requirements = self._analyze_execution_requirements(
            frequency_type, market_type
        )
        
        # 风控需求分析
        risk_controls = self._analyze_risk_controls(
            business_req.risk_tolerance,
            business_req.max_drawdown,
            strategy_type
        )
        
        # 复杂度评估
        complexity, dev_days = self._estimate_complexity(
            strategy_type, frequency_type, market_type,
            len(business_req.special_requirements)
        )
        
        # 依赖分析
        dependencies = self._identify_dependencies(
            strategy_type, market_type, frequency_type
        )
        
        # 技术风险识别
        technical_risks = self._identify_technical_risks(
            strategy_type, frequency_type, market_type
        )
        
        # 生成策略 ID
        strategy_id = self._generate_strategy_id(business_req.strategy_name)
        
        return TechnicalSpecification(
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            market_type=market_type,
            frequency_type=frequency_type,
            data_requirements=data_requirements,
            indicator_requirements=indicator_requirements,
            execution_requirements=execution_requirements,
            risk_controls=risk_controls,
            estimated_complexity=complexity,
            estimated_development_days=dev_days,
            dependencies=dependencies,
            technical_risks=technical_risks
        )
    
    def _identify_strategy_type(self, description: str) -> StrategyType:
        """识别策略类型"""
        desc_lower = description.lower()
        for key, strategy_type in self.strategy_type_mapping.items():
            if key.lower() in desc_lower:
                return strategy_type
        return StrategyType.OTHER
    
    def _identify_market_type(self, market: str) -> MarketType:
        """识别市场类型"""
        market_lower = market.lower()
        for key, market_type in self.market_mapping.items():
            if key.lower() in market_lower:
                return market_type
        return MarketType.US_STOCK  # 默认美股
    
    def _identify_frequency_type(self, frequency: str) -> FrequencyType:
        """识别交易频率"""
        freq_lower = frequency.lower()
        for key, freq_type in self.frequency_mapping.items():
            if key.lower() in freq_lower:
                return freq_type
        return FrequencyType.DAILY  # 默认日线
    
    def _analyze_data_requirements(
        self,
        strategy_type: StrategyType,
        market_type: MarketType,
        frequency_type: FrequencyType
    ) -> Dict[str, Any]:
        """分析数据需求"""
        data_req = {
            "data_sources": [],
            "data_types": [],
            "historical_depth": "1 year",
            "update_frequency": "daily",
            "latency_requirement": "normal"
        }
        
        # 根据频率确定数据更新要求
        if frequency_type == FrequencyType.HIGH_FREQUENCY:
            data_req["update_frequency"] = "real-time"
            data_req["latency_requirement"] = "low (<10ms)"
            data_req["historical_depth"] = "3 months"
        elif frequency_type == FrequencyType.INTRADAY:
            data_req["update_frequency"] = "real-time"
            data_req["latency_requirement"] = "medium (<100ms)"
            data_req["historical_depth"] = "6 months"
        
        # 根据市场确定数据源
        if market_type == MarketType.US_STOCK:
            data_req["data_sources"] = ["polygon", "alpaca", "yfinance"]
        elif market_type == MarketType.A_SHARE:
            data_req["data_sources"] = ["tushare", "baostock", "wind"]
        elif market_type == MarketType.CRYPTO:
            data_req["data_sources"] = ["binance", "coinbase", "ccxt"]
        
        # 根据策略类型确定数据类型
        if strategy_type == StrategyType.HIGH_FREQUENCY:
            data_req["data_types"] = ["tick", "orderbook", "trade"]
        else:
            data_req["data_types"] = ["ohlcv", "adjusted_close"]
        
        return data_req
    
    def _analyze_indicator_requirements(
        self,
        strategy_type: StrategyType,
        description: str
    ) -> List[str]:
        """分析指标需求"""
        indicators = []
        desc_lower = description.lower()
        
        # 趋势跟踪策略指标
        if strategy_type == StrategyType.TREND_FOLLOWING:
            indicators.extend(["MA", "EMA", "MACD", "ADX", "布林带"])
        
        # 均值回归策略指标
        elif strategy_type == StrategyType.MEAN_REVERSION:
            indicators.extend(["RSI", "布林带", "Z-Score", "KDJ"])
        
        # 套利策略指标
        elif strategy_type == StrategyType.ARBITRAGE:
            indicators.extend(["价差", "基差", "协整检验"])
        
        # 因子投资策略指标
        elif strategy_type == StrategyType.FACTOR_INVESTING:
            indicators.extend(["动量因子", "价值因子", "质量因子", "波动率因子"])
        
        # 从描述中提取自定义指标
        indicator_keywords = ["均线", "macd", "rsi", "kdj", "boll", "vol", "volume"]
        for keyword in indicator_keywords:
            if keyword in desc_lower:
                indicators.append(keyword.upper())
        
        return list(set(indicators))  # 去重
    
    def _analyze_execution_requirements(
        self,
        frequency_type: FrequencyType,
        market_type: MarketType
    ) -> Dict[str, Any]:
        """分析执行需求"""
        exec_req = {
            "order_type": "market",
            "execution_speed": "normal",
            "slippage_tolerance": 0.01,
            "position_sizing": "fixed",
            "auto_rebalance": False
        }
        
        # 高频交易需要更快的执行
        if frequency_type == FrequencyType.HIGH_FREQUENCY:
            exec_req["execution_speed"] = "ultra_fast"
            exec_req["order_type"] = "limit"
            exec_req["slippage_tolerance"] = 0.001
        
        # A 股有特殊交易规则
        if market_type == MarketType.A_SHARE:
            exec_req["t_plus_1"] = True
            exec_req["price_limit"] = "10%"
        
        return exec_req
    
    def _analyze_risk_controls(
        self,
        risk_tolerance: str,
        max_drawdown: Optional[float],
        strategy_type: StrategyType
    ) -> List[str]:
        """分析风控需求"""
        controls = []
        
        # 基础风控
        controls.extend([
            "单仓位限制",
            "总仓位限制",
            "止损规则",
            "止盈规则"
        ])
        
        # 根据风险容忍度调整
        if risk_tolerance.lower() == "low":
            controls.extend([
                "严格止损 (2%)",
                "最大仓位 50%",
                "行业分散"
            ])
        elif risk_tolerance.lower() == "high":
            controls.extend([
                "宽松止损 (10%)",
                "最大仓位 100%",
                "集中持仓允许"
            ])
        
        # 根据最大回撤要求
        if max_drawdown:
            if max_drawdown < 0.1:
                controls.append(f"严格回撤控制 (<{max_drawdown*100:.0f}%)")
            elif max_drawdown < 0.2:
                controls.append(f"中等回撤控制 (<{max_drawdown*100:.0f}%)")
            else:
                controls.append(f"宽松回撤控制 (<{max_drawdown*100:.0f}%)")
        
        # 特殊策略风控
        if strategy_type == StrategyType.HIGH_FREQUENCY:
            controls.append("订单频率限制")
            controls.append("撤单率监控")
        
        return controls
    
    def _estimate_complexity(
        self,
        strategy_type: StrategyType,
        frequency_type: FrequencyType,
        market_type: MarketType,
        special_req_count: int
    ) -> tuple[str, int]:
        """估算开发复杂度"""
        base_days = 5  # 基础开发天数
        
        # 策略类型复杂度
        complexity_scores = {
            StrategyType.TREND_FOLLOWING: 1,
            StrategyType.MEAN_REVERSION: 1.5,
            StrategyType.ARBITRAGE: 2,
            StrategyType.MARKET_MAKING: 3,
            StrategyType.FACTOR_INVESTING: 2,
            StrategyType.OTHER: 1.5,
        }
        score = complexity_scores.get(strategy_type, 1.5)
        
        # 频率复杂度
        if frequency_type == FrequencyType.HIGH_FREQUENCY:
            score *= 2
            base_days += 10
        elif frequency_type == FrequencyType.INTRADAY:
            score *= 1.5
            base_days += 5
        
        # 市场复杂度
        if market_type == MarketType.A_SHARE:
            score *= 1.2  # A 股规则复杂
        
        # 特殊需求
        score += special_req_count * 0.2
        
        # 计算最终天数
        dev_days = int(base_days * score)
        
        # 确定复杂度等级
        if score < 2:
            complexity = "low"
        elif score < 4:
            complexity = "medium"
        else:
            complexity = "high"
        
        return complexity, dev_days
    
    def _identify_dependencies(
        self,
        strategy_type: StrategyType,
        market_type: MarketType,
        frequency_type: FrequencyType
    ) -> List[str]:
        """识别依赖项"""
        dependencies = ["基础数据模块", "回测引擎"]
        
        if frequency_type in [FrequencyType.HIGH_FREQUENCY, FrequencyType.INTRADAY]:
            dependencies.append("实时数据流")
            dependencies.append("低延迟执行模块")
        
        if strategy_type == StrategyType.FACTOR_INVESTING:
            dependencies.append("因子计算库")
            dependencies.append("基本面数据")
        
        if market_type == MarketType.A_SHARE:
            dependencies.append("A 股交易规则模块")
        
        return dependencies
    
    def _identify_technical_risks(
        self,
        strategy_type: StrategyType,
        frequency_type: FrequencyType,
        market_type: MarketType
    ) -> List[str]:
        """识别技术风险"""
        risks = []
        
        if frequency_type == FrequencyType.HIGH_FREQUENCY:
            risks.extend([
                "网络延迟风险",
                "系统稳定性风险",
                "数据丢失风险"
            ])
        
        if market_type == MarketType.A_SHARE:
            risks.append("交易规则变更风险")
        
        if strategy_type == StrategyType.ARBITRAGE:
            risks.append("价差消失风险")
            risks.append("执行不同步风险")
        
        risks.append("过拟合风险")
        risks.append("市场制度变化风险")
        
        return risks
    
    def _generate_strategy_id(self, strategy_name: str) -> str:
        """生成策略 ID"""
        import hashlib
        timestamp = datetime.now().strftime("%Y%m%d")
        name_hash = hashlib.md5(strategy_name.encode()).hexdigest()[:6]
        return f"STRAT_{timestamp}_{name_hash.upper()}"
    
    def generate_requirement_doc(
        self,
        business_req: BusinessRequirement,
        tech_spec: TechnicalSpecification
    ) -> str:
        """生成需求文档"""
        doc = f"""# 策略需求文档

## 基本信息
- **策略名称**: {business_req.strategy_name}
- **策略 ID**: {tech_spec.strategy_id}
- **文档生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **复杂度评估**: {tech_spec.estimated_complexity.upper()}
- **预计开发周期**: {tech_spec.estimated_development_days} 天

## 业务需求概述
{business_req.strategy_description}

### 业务目标
- 期望年化收益：{business_req.expected_return if business_req.expected_return else '未指定'}
- 最大可接受回撤：{business_req.max_drawdown if business_req.max_drawdown else '未指定'}
- 风险容忍度：{business_req.risk_tolerance}
- 目标市场：{business_req.target_market}
- 交易频率：{business_req.trading_frequency}

## 技术规格

### 策略分类
- 策略类型：{tech_spec.strategy_type.value}
- 市场类型：{tech_spec.market_type.value}
- 频率类型：{tech_spec.frequency_type.value}

### 数据需求
- 数据源：{', '.join(tech_spec.data_requirements.get('data_sources', []))}
- 数据类型：{', '.join(tech_spec.data_requirements.get('data_types', []))}
- 历史深度：{tech_spec.data_requirements.get('historical_depth', 'N/A')}
- 更新频率：{tech_spec.data_requirements.get('update_frequency', 'N/A')}
- 延迟要求：{tech_spec.data_requirements.get('latency_requirement', 'N/A')}

### 技术指标
{chr(10).join(['- ' + ind for ind in tech_spec.indicator_requirements])}

### 执行要求
- 订单类型：{tech_spec.execution_requirements.get('order_type', 'N/A')}
- 执行速度：{tech_spec.execution_requirements.get('execution_speed', 'N/A')}
- 滑点容忍：{tech_spec.execution_requirements.get('slippage_tolerance', 'N/A')}
- 仓位管理：{tech_spec.execution_requirements.get('position_sizing', 'N/A')}

### 风控措施
{chr(10).join(['- ' + ctrl for ctrl in tech_spec.risk_controls])}

## 开发评估

### 依赖模块
{chr(10).join(['- ' + dep for dep in tech_spec.dependencies])}

### 技术风险
{chr(10).join(['- ' + risk for risk in tech_spec.technical_risks])}

### 特殊要求
{chr(10).join(['- ' + req for req in business_req.special_requirements]) if business_req.special_requirements else '无'}

## 下一步行动
1. [ ] 技术评审会议
2. [ ] 确认数据源接入
3. [ ] 开发环境准备
4. [ ] 开始实现

---
*文档由 RequirementTranslator 自动生成*
"""
        return doc


# 使用示例
if __name__ == "__main__":
    # 示例业务需求
    business_req = BusinessRequirement(
        strategy_name="双均线趋势策略",
        strategy_description="基于短期和长期均线交叉的趋势跟踪策略，在美股市场交易",
        expected_return=0.15,
        max_drawdown=0.1,
        trading_frequency="日线",
        target_market="美股",
        capital_requirement=100000,
        risk_tolerance="medium",
        special_requirements=["需要支持多股票组合", "需要实时风控监控"]
    )
    
    # 翻译需求
    translator = RequirementTranslator()
    tech_spec = translator.translate(business_req)
    
    # 生成文档
    doc = translator.generate_requirement_doc(business_req, tech_spec)
    print(doc)
    
    # 保存文档
    with open(f"requirement_{tech_spec.strategy_id}.md", "w", encoding="utf-8") as f:
        f.write(doc)
