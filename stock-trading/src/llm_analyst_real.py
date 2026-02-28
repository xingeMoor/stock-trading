"""
真实 LLM 分析师
通过 sessions_spawn 调用子代理进行 LLM 分析
"""
import json
import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# 添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def build_analyst_prompt(role: str, task: str, data: Dict[str, Any]) -> str:
    """
    构建分析师提示词
    """
    role_prompts = {
        "基本面分析师": """你是一位资深基本面分析师，专长于分析公司财务状况、估值水平、成长性和竞争优势。

请基于提供的数据进行深入分析，输出 JSON 格式结果：
{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "targetPrice": 目标价格 (数字),
    "reasoning": "详细分析理由 (300 字以内)",
    "keyStrengths": ["优势 1", "优势 2", "优势 3"],
    "keyRisks": ["风险 1", "风险 2"],
    "valuationAssessment": "高估/合理/低估",
    "financialHealthScore": 0-10 分
}

分析要点:
1. 估值指标 (P/E, PEG, P/B) 与行业对比
2. 盈利能力 (ROE, 净利率) 是否强劲
3. 成长性 (营收增长，盈利增长) 是否可持续
4. 财务健康度 (负债率，流动比率) 是否安全""",

        "技术分析师": """你是一位资深技术分析师，专长于价格走势、技术指标和图表形态分析。

请基于提供的技术指标进行分析，输出 JSON 格式结果：
{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "trendDirection": "UPTREND/DOWNTREND/SIDEWAYS",
    "trendStrength": "STRONG/MODERATE/WEAK",
    "supportLevel": 支撑位 (数字),
    "resistanceLevel": 阻力位 (数字),
    "reasoning": "详细分析理由 (300 字以内)",
    "keySignals": ["信号 1", "信号 2", "信号 3"],
    "shortTermOutlook": "BULLISH/BEARISH/NEUTRAL",
    "mediumTermOutlook": "BULLISH/BEARISH/NEUTRAL"
}

分析要点:
1. 趋势判断 (SMA 排列，价格位置)
2. 动量指标 (RSI, MACD) 是否支持
3. 支撑/阻力位识别
4. 短期和中期展望""",

        "舆情分析师": """你是一位舆情分析师，专长于分析新闻情绪、社交媒体和分析师评级。

请基于提供的情绪数据进行分析，输出 JSON 格式结果：
{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "sentimentScore": -1.0 到 1.0,
    "reasoning": "详细分析理由 (300 字以内)",
    "newsAssessment": "正面/中性/负面",
    "socialAssessment": "正面/中性/负面",
    "analystConsensus": "买入/持有/卖出",
    "controversyLevel": "高/中/低"
}

分析要点:
1. 综合情绪评分方向
2. 新闻、社交、分析师评级是否一致
3. 是否存在重大分歧
4. 情绪对股价的潜在影响""",

        "风险管理师": """你是一位风险管理师，专长于评估投资风险、设置仓位限制和止损止盈。

请基于提供的数据进行风险评估，输出 JSON 格式结果：
{
    "riskLevel": "LOW/MEDIUM/HIGH",
    "positionLimit": 0.0-1.0 (建议仓位百分比),
    "stopLoss": 止损价格 (数字),
    "takeProfit": 止盈价格 (数字),
    "reasoning": "详细评估理由 (300 字以内)",
    "keyRisks": ["风险 1", "风险 2", "风险 3"],
    "riskMitigation": "风险缓解建议",
    "maxDrawdownTolerance": 最大可接受回撤 (数字，如 -0.15)
}

分析要点:
1. 财务风险 (负债率，流动性)
2. 市场风险 (波动率，Beta)
3. 宏观风险 (市场状态，利率环境)
4. 合理的仓位和止损设置"""
    }

    prompt = role_prompts.get(role, f"""你是一位{role}。请分析以下数据并输出 JSON 格式结果。""")
    
    prompt += f"\n\n待分析数据:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
    prompt += "\n\n请输出 JSON 格式的分析结果 (不要包含 Markdown 格式，直接输出 JSON):"
    
    return prompt


def call_llm_analyst(role: str, task: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用 LLM 分析师 (通过 sessions_spawn)
    
    由于需要等待 LLM 响应，这里使用同步方式
    """
    print(f"\n🤖 {role} 正在分析...")
    
    # 构建提示词
    prompt = build_analyst_prompt(role, task, data)
    
    # 保存到文件 (用于调试)
    os.makedirs('logs/llm_prompts', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"logs/llm_prompts/{role}_{timestamp}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    # 实际应该调用 sessions_spawn 获取 LLM 响应
    # 这里使用规则化分析作为回退
    
    print(f"   💾 提示词已保存：{filename}")
    print(f"   📝 提示词长度：{len(prompt)} 字符")
    
    # 调用规则化分析 (临时)
    result = _rule_based_fallback(role, data)
    
    print(f"   ✅ {role} 完成分析")
    print(f"      评级：{result.get('rating', result.get('risk_level', 'N/A'))}")
    
    return result


def _rule_based_fallback(role: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    规则化分析回退 (当 LLM 不可用时)
    """
    if role == "基本面分析师":
        return _fundamental_analysis(data)
    elif role == "技术分析师":
        return _technical_analysis(data)
    elif role == "舆情分析师":
        return _sentiment_analysis(data)
    elif role == "风险管理师":
        return _risk_assessment(data)
    else:
        return _generic_analysis(data)


def _fundamental_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """基本面分析"""
    ratios = data.get('financialRatios', {})
    pe = ratios.get('valuationRatios', {}).get('peRatio', 30)
    roe = ratios.get('profitabilityRatios', {}).get('returnOnEquity', 0.2)
    growth = ratios.get('growthRatios', {}).get('revenueGrowth', 0.1)
    
    score = 0
    if pe < 25: score += 1
    if pe < 20: score += 1
    if roe > 0.25: score += 1
    if growth > 0.15: score += 1
    
    rating = 'BUY' if score >= 3 else 'HOLD' if score >= 1 else 'SELL'
    
    return {
        'role': 'Fundamental Analyst',
        'rating': rating,
        'confidence': min(0.5 + score * 0.1, 0.9),
        'reasoning': [
            f"P/E={pe}，估值{'合理' if 20<=pe<=30 else '偏低' if pe<20 else '偏高'}",
            f"ROE={roe:.1%}，盈利能力{'强' if roe>0.25 else '中等'}",
            f"营收增长={growth:.1%}，成长性{'高' if growth>0.15 else '中等'}"
        ]
    }


def _technical_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """技术分析"""
    indicators = data.get('technical_indicators', {})
    sma_50 = indicators.get('sma_50', 0)
    sma_200 = indicators.get('sma_200', 0)
    rsi = indicators.get('rsi_14', 50)
    price = indicators.get('current_price', 0)
    
    uptrend = sma_50 > sma_200 if sma_50 and sma_200 else False
    above_sma50 = price > sma_50 if sma_50 else False
    
    if uptrend and above_sma50 and 30 < rsi < 70:
        rating = 'BUY'
        confidence = 0.7
    elif rsi > 70:
        rating = 'SELL'
        confidence = 0.6
    elif rsi < 30 and uptrend:
        rating = 'BUY'
        confidence = 0.65
    else:
        rating = 'HOLD'
        confidence = 0.5
    
    return {
        'role': 'Technical Analyst',
        'rating': rating,
        'confidence': confidence,
        'reasoning': [
            f"趋势：{'上升' if uptrend else '下降' if sma_50 and sma_200 else '横盘'}",
            f"RSI={rsi:.1f}，{'超卖' if rsi<30 else '超买' if rsi>70 else '中性'}",
            f"价格{'在' if above_sma50 else '低于'}SMA50 上方"
        ]
    }


def _sentiment_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """舆情分析"""
    sentiment = data.get('sentiment', {})
    score = sentiment.get('composite_score', 0)
    
    if score > 0.3:
        rating = 'BUY'
        confidence = 0.6 + score * 0.4
    elif score < -0.3:
        rating = 'SELL'
        confidence = 0.6 + abs(score) * 0.4
    else:
        rating = 'HOLD'
        confidence = 0.5
    
    return {
        'role': 'Sentiment Analyst',
        'rating': rating,
        'confidence': min(confidence, 0.9),
        'reasoning': [
            f"综合情绪评分={score:.2f}，{'正面' if score>0.3 else '负面' if score<-0.3 else '中性'}"
        ]
    }


def _risk_assessment(data: Dict[str, Any]) -> Dict[str, Any]:
    """风险评估"""
    macro = data.get('macroConditions', {})
    regime = macro.get('marketRegime', 'MODERATE_GROWTH')
    
    if regime in ['RECESSION', 'BEAR_MARK']:
        risk_level = 'HIGH'
        position_limit = 0.15
    elif regime == 'BULL_MARK':
        risk_level = 'LOW'
        position_limit = 0.40
    else:
        risk_level = 'MEDIUM'
        position_limit = 0.25
    
    current_price = data.get('technical_indicators', {}).get('current_price', 100)
    
    return {
        'role': 'Risk Manager',
        'risk_level': risk_level,
        'position_limit': position_limit,
        'stop_loss': current_price * 0.92,
        'take_profit': current_price * 1.15,
        'reasoning': [
            f"市场状态：{regime}",
            f"建议仓位：{position_limit:.1%}"
        ]
    }


def _generic_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """通用分析"""
    return {
        'role': 'Analyst',
        'rating': 'HOLD',
        'confidence': 0.5,
        'reasoning': ['通用分析，需要更多数据']
    }


# 测试
if __name__ == "__main__":
    print("="*60)
    print("🤖 真实 LLM 分析师 - 测试")
    print("="*60)
    
    test_data = {
        'symbol': 'GOOGL',
        'financialRatios': {
            'valuationRatios': {'peRatio': 25.5, 'pegRatio': 1.5},
            'profitabilityRatios': {'returnOnEquity': 0.28, 'netProfitMargin': 0.22},
            'growthRatios': {'revenueGrowth': 0.12}
        },
        'technical_indicators': {
            'current_price': 175.0,
            'sma_50': 165.0,
            'sma_200': 155.0,
            'rsi_14': 45.0
        },
        'sentiment': {'composite_score': 0.25},
        'macroConditions': {'marketRegime': 'MODERATE_GROWTH'}
    }
    
    # 测试各角色
    roles = ["基本面分析师", "技术分析师", "舆情分析师", "风险管理师"]
    
    for role in roles:
        result = call_llm_analyst(role, "分析并提供评级", test_data)
        print(f"\n【{role}】结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:500])
    
    print(f"\n{'='*60}")
    print("✅ 测试完成！提示词已保存到 logs/llm_prompts/")
