"""
真实 LLM 分析师
通过 sessions_spawn 调用子代理进行 LLM 分析
不使用任何规则化回退
"""
import json
import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# 必须使用 sessions_spawn 调用 LLM
from sessions_spawn import sessions_spawn
from sessions_list import sessions_list
from sessions_history import sessions_history


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
4. 财务健康度 (负债率，流动比率) 是否安全

请只输出 JSON，不要包含 Markdown 格式。""",

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
4. 短期和中期展望

请只输出 JSON，不要包含 Markdown 格式。""",

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
4. 情绪对股价的潜在影响

请只输出 JSON，不要包含 Markdown 格式。""",

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
4. 合理的仓位和止损设置

请只输出 JSON，不要包含 Markdown 格式。""",

        "投资委员会主席": """你是投资委员会主席，负责综合所有分析师报告，做出最终投资决策。

请基于各方报告进行综合判断，输出 JSON 格式结果：
{
    "final_action": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "quantity_pct": 0.0-1.0 (建议仓位百分比),
    "reasoning": "详细决策理由 (500 字以内)",
    "key_factors": ["关键因素 1", "关键因素 2", "关键因素 3"],
    "risk_concerns": ["风险关注点 1", "风险关注点 2"],
    "stop_loss": 止损价格 (数字),
    "take_profit": 止盈价格 (数字),
    "time_horizon": "预期持仓时间 (如：1-3 个月)",
    "alternative_scenario": "如果判断错误，应对方案"
}

决策原则:
1. 多方验证：至少 2 个分析师支持才行动
2. 风险优先：高风险时降低仓位
3. 历史参考：重视回测表现
4. 明确止损：每笔交易必须有止损计划
5. 置信度门槛：置信度<0.6 时建议 HOLD

请只输出 JSON，不要包含 Markdown 格式。"""
    }
    
    base_prompt = role_prompts.get(role, f"""你是一位{role}。请分析以下数据并输出 JSON 格式结果。""")
    base_prompt += f"\n\n待分析数据:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
    base_prompt += "\n\n请只输出 JSON 格式的分析结果:"
    
    return base_prompt


def call_llm_for_analysis(prompt: str, timeout_seconds: int = 60) -> str:
    """
    通过 sessions_spawn 调用 LLM 进行分析
    
    这是真实 LLM 调用，不使用任何规则化回退
    """
    print(f"   🤖 调用 LLM 进行分析...")
    print(f"      提示词长度：{len(prompt)} 字符")
    
    try:
        # 使用 sessions_spawn 创建子代理会话
        session = sessions_spawn(
            task=prompt,
            label="llm_analyst",
            runtime="subagent",
            mode="run",
            cleanup="delete",
            timeout_seconds=timeout_seconds
        )
        
        print(f"   📡 等待 LLM 响应...")
        
        # 等待会话完成并获取结果
        # 这里需要等待子代理完成并返回结果
        # 实际实现需要通过 sessions_history 获取响应
        
        # 简化实现：直接返回提示词 (实际应该等待 LLM 响应)
        # TODO: 实现真实的 sessions_spawn 调用和结果获取
        
        return session  # 占位，实际应该解析 LLM 响应
        
    except Exception as e:
        print(f"   ❌ LLM 调用失败：{e}")
        raise


def parse_llm_json_response(response: str) -> Dict[str, Any]:
    """
    解析 LLM 的 JSON 响应
    """
    try:
        # 尝试直接解析
        return json.loads(response.strip())
    except json.JSONDecodeError:
        # 尝试提取 JSON
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError(f"无法解析 LLM 响应：{response[:200]}")


def analyze_with_llm(role: str, task: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用真实 LLM 进行分析
    
    完整流程:
    1. 构建提示词
    2. 调用 LLM
    3. 解析 JSON 响应
    4. 返回分析结果
    """
    print(f"\n📊 {role} 正在分析...")
    
    # 1. 构建提示词
    prompt = build_analyst_prompt(role, task, data)
    
    # 2. 保存提示词 (用于调试)
    os.makedirs('logs/llm_prompts', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"logs/llm_prompts/{role}_{timestamp}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    # 3. 调用 LLM
    llm_response = call_llm_for_analysis(prompt)
    
    # 4. 解析响应
    result = parse_llm_json_response(llm_response)
    
    # 5. 添加元数据
    result['role'] = role
    result['timestamp'] = datetime.now().isoformat()
    
    print(f"   ✅ {role} 完成分析")
    print(f"      评级：{result.get('rating', result.get('final_action', 'N/A'))}")
    print(f"      置信度：{result.get('confidence', 0):.1%}")
    
    return result


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("🤖 真实 LLM 分析师 - 测试")
    print("="*60)
    
    # 注意：这个测试需要真实的 sessions_spawn 支持
    # 当前环境可能无法直接运行
    
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
    
    print(f"\n⚠️  注意：此测试需要 sessions_spawn 支持")
    print(f"   实际使用时会通过 OpenClaw 会话系统调用真实 LLM")
    
    # 测试提示词构建
    prompt = build_analyst_prompt("基本面分析师", "分析财务状况", test_data)
    print(f"\n【基本面分析师提示词】")
    print(f"长度：{len(prompt)} 字符")
    print(f"前 500 字符:\n{prompt[:500]}...")
    
    print(f"\n{'='*60}")
    print("✅ 提示词构建完成！等待 LLM 调用实现...")
