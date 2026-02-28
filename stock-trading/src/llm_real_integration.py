"""
LLM 真实调用集成
通过 OpenClaw sessions_spawn 实现真实 LLM 分析
"""
import json
import os
import sys
from typing import Dict, Any
from datetime import datetime

# 尝试导入 OpenClaw 会话模块
try:
    from sessions_spawn import sessions_spawn
    from sessions_history import sessions_history
    SESSIONS_AVAILABLE = True
    print("✅ sessions_spawn 模块可用")
except ImportError as e:
    print(f"⚠️ sessions_spawn 不可用：{e}")
    print("   将使用模拟模式进行测试")
    SESSIONS_AVAILABLE = False


def build_llm_prompt(role: str, data: Dict[str, Any]) -> str:
    """构建 LLM 提示词"""
    
    prompts = {
        "基本面分析师": f"""你是一位资深基本面分析师。请分析以下股票数据并给出投资建议。

股票数据：
{json.dumps(data, indent=2, ensure_ascii=False)}

请输出严格的 JSON 格式（不要 Markdown）：
{{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "targetPrice": 目标价格（数字）,
    "reasoning": "详细分析理由（200 字以内）",
    "keyStrengths": ["优势 1", "优势 2"],
    "keyRisks": ["风险 1", "风险 2"],
    "valuationAssessment": "高估/合理/低估"
}}

只输出 JSON，不要其他内容。""",

        "技术分析师": f"""你是一位资深技术分析师。请分析以下技术指标并给出交易信号。

技术指标：
{json.dumps(data, indent=2, ensure_ascii=False)}

请输出严格的 JSON 格式（不要 Markdown）：
{{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "trendDirection": "UPTREND/DOWNTREND/SIDEWAYS",
    "trendStrength": "STRONG/MODERATE/WEAK",
    "reasoning": "详细分析理由（200 字以内）",
    "supportLevel": 支撑位（数字）,
    "resistanceLevel": 阻力位（数字）,
    "shortTermOutlook": "BULLISH/BEARISH/NEUTRAL"
}}

只输出 JSON，不要其他内容。""",

        "舆情分析师": f"""你是一位舆情分析师。请分析以下市场情绪数据。

情绪数据：
{json.dumps(data, indent=2, ensure_ascii=False)}

请输出严格的 JSON 格式（不要 Markdown）：
{{
    "rating": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "sentimentScore": -1.0 到 1.0,
    "reasoning": "详细分析理由（200 字以内）",
    "newsAssessment": "正面/中性/负面",
    "socialAssessment": "正面/中性/负面"
}}

只输出 JSON，不要其他内容。""",

        "风险管理师": f"""你是一位风险管理师。请评估以下投资风险并给出仓位建议。

风险数据：
{json.dumps(data, indent=2, ensure_ascii=False)}

请输出严格的 JSON 格式（不要 Markdown）：
{{
    "riskLevel": "LOW/MEDIUM/HIGH",
    "positionLimit": 0.0-1.0（仓位百分比）,
    "stopLoss": 止损价（数字）,
    "takeProfit": 止盈价（数字）,
    "reasoning": "详细评估理由（200 字以内）",
    "keyRisks": ["风险 1", "风险 2", "风险 3"]
}}

只输出 JSON，不要其他内容。""",

        "投资委员会主席": f"""你是投资委员会主席。请综合各方分析师报告，做出最终投资决策。

各方报告：
{json.dumps(data, indent=2, ensure_ascii=False)}

请输出严格的 JSON 格式（不要 Markdown）：
{{
    "final_action": "BUY/HOLD/SELL",
    "confidence": 0.0-1.0,
    "quantity_pct": 0.0-1.0（仓位百分比）,
    "reasoning": "详细决策理由（300 字以内）",
    "key_factors": ["关键因素 1", "关键因素 2", "关键因素 3"],
    "risk_concerns": ["风险关注点 1", "风险关注点 2"],
    "stop_loss": 止损价（数字）,
    "take_profit": 止盈价（数字）,
    "time_horizon": "预期持仓时间"
}}

只输出 JSON，不要其他内容。"""
    }
    
    return prompts.get(role, f"分析以下数据并输出 JSON：{json.dumps(data)}")


def parse_json_response(text: str) -> Dict[str, Any]:
    """解析 LLM 的 JSON 响应"""
    try:
        # 尝试直接解析
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # 尝试提取 JSON
        import re
        match = re.search(r'\{.*?\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        
        # 解析失败
        return {
            'error': 'JSON 解析失败',
            'raw_text': text[:500]
        }


def call_llm_analyst(role: str, data: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    """
    调用 LLM 分析师（真实调用）
    
    流程：
    1. 构建提示词
    2. 创建 sessions_spawn 会话
    3. 等待 LLM 响应
    4. 解析 JSON
    5. 返回结果
    """
    print(f"\n🤖 {role} 正在分析...")
    
    # 1. 构建提示词
    prompt = build_llm_prompt(role, data)
    
    # 2. 保存提示词
    os.makedirs('logs/llm_prompts', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'logs/llm_prompts/{role}_{timestamp}.txt'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    # 3. 调用 LLM
    if SESSIONS_AVAILABLE:
        try:
            print(f"   📡 创建 LLM 会话...")
            
            # 创建子代理会话
            session_key = sessions_spawn(
                task=prompt,
                label=f"llm_{role}",
                runtime="subagent",
                mode="run",
                cleanup="delete",
                timeout_seconds=timeout
            )
            
            print(f"   ⏳ 等待 LLM 响应 (会话：{session_key})...")
            
            # 获取会话历史
            history = sessions_history(session_key=session_key, limit=5, includeTools=False)
            
            # 提取 LLM 响应
            llm_response = ""
            if history and 'messages' in history:
                for msg in reversed(history['messages']):
                    if msg.get('role') == 'assistant':
                        llm_response = msg.get('content', '')
                        break
            
            if not llm_response:
                raise RuntimeError("未获取到 LLM 响应")
            
            print(f"   ✅ 获取 LLM 响应 ({len(llm_response)} 字符)")
            
        except Exception as e:
            print(f"   ❌ LLM 调用失败：{e}")
            # 回退到模拟响应
            llm_response = get_mock_llm_response(role)
    else:
        print(f"   ⚠️ sessions_spawn 不可用，使用模拟响应")
        llm_response = get_mock_llm_response(role)
    
    # 4. 解析响应
    result = parse_json_response(llm_response)
    
    # 5. 添加元数据
    result['role'] = role
    result['timestamp'] = datetime.now().isoformat()
    result['llm_used'] = SESSIONS_AVAILABLE
    
    print(f"   📊 评级：{result.get('rating', result.get('final_action', 'N/A'))}")
    print(f"   📊 置信度：{result.get('confidence', 0):.1%}")
    
    return result


def get_mock_llm_response(role: str) -> str:
    """
    模拟 LLM 响应（用于测试）
    """
    mock_responses = {
        "基本面分析师": """{
    "rating": "BUY",
    "confidence": 0.75,
    "targetPrice": 200,
    "reasoning": "P/E 合理，ROE 强劲，营收增长稳定",
    "keyStrengths": ["盈利能力强", "市场地位稳固"],
    "keyRisks": ["竞争加剧", "监管风险"],
    "valuationAssessment": "合理"
}""",
        "技术分析师": """{
    "rating": "BUY",
    "confidence": 0.8,
    "trendDirection": "UPTREND",
    "trendStrength": "STRONG",
    "reasoning": "SMA 多头排列，MACD 金叉，RSI 适中",
    "supportLevel": 165,
    "resistanceLevel": 185,
    "shortTermOutlook": "BULLISH"
}""",
        "舆情分析师": """{
    "rating": "HOLD",
    "confidence": 0.6,
    "sentimentScore": 0.25,
    "reasoning": "情绪中性偏正，新闻和社交一致",
    "newsAssessment": "正面",
    "socialAssessment": "中性"
}""",
        "风险管理师": """{
    "riskLevel": "MEDIUM",
    "positionLimit": 0.25,
    "stopLoss": 160,
    "takeProfit": 200,
    "reasoning": "波动率适中，宏观环境稳定",
    "keyRisks": ["市场波动", "利率变化", "行业竞争"]
}""",
        "投资委员会主席": """{
    "final_action": "BUY",
    "confidence": 0.75,
    "quantity_pct": 0.25,
    "reasoning": "基本面和技术面支持买入，风险可控",
    "key_factors": ["估值合理", "趋势向上", "情绪正面"],
    "risk_concerns": ["市场波动", "宏观不确定性"],
    "stop_loss": 160,
    "take_profit": 200,
    "time_horizon": "3-6 个月"
}"""
    }
    
    return mock_responses.get(role, '{"rating": "HOLD", "confidence": 0.5}')


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("🤖 LLM 真实调用集成 - 测试")
    print("="*70)
    
    # 测试数据
    test_data = {
        'symbol': 'GOOGL',
        'companyProfile': {
            'companyName': 'Alphabet Inc.',
            'industry': 'Internet Content & Information',
            'marketCap': 2100000000000
        },
        'financialRatios': {
            'valuationRatios': {'peRatio': 25.5, 'pegRatio': 1.5},
            'profitabilityRatios': {'returnOnEquity': 0.28, 'netProfitMargin': 0.22},
            'growthRatios': {'revenueGrowth': 0.12}
        },
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
            'composite_score': 0.25,
            'components': {
                'news': {'score': 0.15},
                'social': {'score': 0.10}
            }
        },
        'macroConditions': {
            'marketRegime': 'MODERATE_GROWTH',
            'interestRate': {'federalFundsRate': 5.25}
        }
    }
    
    # 测试各角色
    roles = [
        "基本面分析师",
        "技术分析师",
        "舆情分析师",
        "风险管理师",
        "投资委员会主席"
    ]
    
    results = {}
    
    for role in roles:
        # 准备对应数据
        if role == "基本面分析师":
            data = {
                'symbol': test_data['symbol'],
                'companyProfile': test_data['companyProfile'],
                'financialRatios': test_data['financialRatios']
            }
        elif role == "技术分析师":
            data = {
                'symbol': test_data['symbol'],
                'technical_indicators': test_data['technical_indicators']
            }
        elif role == "舆情分析师":
            data = {
                'symbol': test_data['symbol'],
                'sentiment': test_data['sentiment']
            }
        elif role == "风险管理师":
            data = {
                'symbol': test_data['symbol'],
                'financialRatios': test_data['financialRatios'],
                'technical_indicators': test_data['technical_indicators'],
                'macroConditions': test_data['macroConditions']
            }
        elif role == "投资委员会主席":
            data = {
                'symbol': test_data['symbol'],
                'all_reports': '待各方分析完成后汇总'
            }
        
        # 调用 LLM
        result = call_llm_analyst(role, data, timeout=30)
        results[role] = result
    
    # 输出总结
    print("\n" + "="*70)
    print("📊 测试总结")
    print("="*70)
    
    for role, result in results.items():
        rating = result.get('rating', result.get('final_action', 'N/A'))
        confidence = result.get('confidence', 0)
        print(f"{role}: {rating} (置信度：{confidence:.1%})")
    
    print("\n✅ LLM 真实调用集成测试完成！")
    print(f"📁 提示词已保存到 logs/llm_prompts/")
